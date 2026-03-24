"""2D representation caching for floor plan generation.

RepresentationCache stores computed 2D linework to avoid redundant
section cut calculations when generating floor plans.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bimascode.core.element import Element


@dataclass
class CachedRepresentation:
    """Cached 2D representation data for an element.

    Stores the computed 2D linework along with metadata for
    cache invalidation.
    """

    element_id: int  # id() of the element
    cut_height: float  # Z height of the section cut
    linework: Any  # The cached 2D geometry (lines, arcs, etc.)
    timestamp: float  # When this was cached
    element_modified: float  # Element's modification timestamp when cached

    def is_valid(self, element_modified: float) -> bool:
        """Check if this cached representation is still valid.

        Args:
            element_modified: Current modification timestamp of the element

        Returns:
            True if cache is still valid
        """
        return self.element_modified >= element_modified


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""

    hits: int = 0
    misses: int = 0
    invalidations: int = 0
    total_compute_time_saved: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Return the cache hit rate as a percentage."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100.0


class RepresentationCache:
    """Cache for 2D representations of BIM elements.

    Stores computed section cuts to avoid redundant calculations
    when regenerating floor plans. The cache automatically invalidates
    entries when elements are modified.

    Example:
        >>> cache = RepresentationCache()
        >>> linework = cache.get_or_compute(wall, cut_height=1200, compute_func)
        >>> # Second call uses cached value
        >>> linework = cache.get_or_compute(wall, cut_height=1200, compute_func)
    """

    def __init__(self, max_entries: int = 10000):
        """Initialize the representation cache.

        Args:
            max_entries: Maximum number of cached entries before eviction
        """
        # Key: (element_id, cut_height) -> CachedRepresentation
        self._cache: dict[tuple[int, float], CachedRepresentation] = {}
        self._max_entries = max_entries
        self._stats = CacheStats()
        # Track access order for LRU eviction
        self._access_order: list[tuple[int, float]] = []

    def get(self, element: Element, cut_height: float) -> Any | None:
        """Get a cached 2D representation if available and valid.

        Args:
            element: The element to get representation for
            cut_height: Z height of the section cut

        Returns:
            Cached linework if valid, None otherwise
        """
        key = (id(element), cut_height)

        if key not in self._cache:
            return None

        cached = self._cache[key]

        # Check if element has been modified
        element_modified = getattr(element, "_modified_timestamp", 0)

        if not cached.is_valid(element_modified):
            # Cache is stale
            del self._cache[key]
            self._stats.invalidations += 1
            return None

        # Update access order for LRU
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        self._stats.hits += 1
        return cached.linework

    def put(
        self,
        element: Element,
        cut_height: float,
        linework: Any,
        compute_time: float = 0.0,
    ) -> None:
        """Store a 2D representation in the cache.

        Args:
            element: The element this representation is for
            cut_height: Z height of the section cut
            linework: The 2D geometry to cache
            compute_time: Time taken to compute (for stats)
        """
        key = (id(element), cut_height)

        # Evict if at capacity
        if len(self._cache) >= self._max_entries and key not in self._cache:
            self._evict_oldest()

        # Get element's modification timestamp
        element_modified = getattr(element, "_modified_timestamp", time.time())

        self._cache[key] = CachedRepresentation(
            element_id=id(element),
            cut_height=cut_height,
            linework=linework,
            timestamp=time.time(),
            element_modified=element_modified,
        )

        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def get_or_compute(
        self,
        element: Element,
        cut_height: float,
        compute_func: callable,
    ) -> Any:
        """Get cached representation or compute and cache it.

        This is the primary interface for using the cache. It handles
        cache lookup, computation on miss, and storage automatically.

        Args:
            element: The element to get representation for
            cut_height: Z height of the section cut
            compute_func: Function to call if cache miss (element, cut_height) -> linework

        Returns:
            The 2D linework (cached or freshly computed)
        """
        # Try cache first
        cached = self.get(element, cut_height)
        if cached is not None:
            return cached

        # Cache miss - compute
        self._stats.misses += 1

        start_time = time.time()
        linework = compute_func(element, cut_height)
        compute_time = time.time() - start_time

        # Store in cache
        self.put(element, cut_height, linework, compute_time)

        return linework

    def invalidate(self, element: Element) -> int:
        """Invalidate all cached representations for an element.

        Call this when an element's geometry changes.

        Args:
            element: The modified element

        Returns:
            Number of cache entries invalidated
        """
        element_id = id(element)
        keys_to_remove = [key for key in self._cache if key[0] == element_id]

        for key in keys_to_remove:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)

        self._stats.invalidations += len(keys_to_remove)
        return len(keys_to_remove)

    def invalidate_cut_height(self, cut_height: float) -> int:
        """Invalidate all cached representations at a specific cut height.

        Args:
            cut_height: The cut height to invalidate

        Returns:
            Number of cache entries invalidated
        """
        keys_to_remove = [key for key in self._cache if key[1] == cut_height]

        for key in keys_to_remove:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)

        self._stats.invalidations += len(keys_to_remove)
        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cached representations."""
        count = len(self._cache)
        self._cache.clear()
        self._access_order.clear()
        self._stats.invalidations += count

    def _evict_oldest(self) -> None:
        """Evict the least recently used entry."""
        if self._access_order:
            oldest_key = self._access_order.pop(0)
            if oldest_key in self._cache:
                del self._cache[oldest_key]

    @property
    def stats(self) -> CacheStats:
        """Return cache statistics."""
        return self._stats

    @property
    def size(self) -> int:
        """Return the number of cached entries."""
        return len(self._cache)

    def __len__(self) -> int:
        """Return the number of cached entries."""
        return len(self._cache)

    def __contains__(self, element: Element) -> bool:
        """Check if any representation for an element is cached."""
        element_id = id(element)
        return any(key[0] == element_id for key in self._cache)
