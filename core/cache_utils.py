"""
Cache utility functions for Django REST Framework views.

Provides decorators and helpers for caching API responses with Redis.
"""
from functools import wraps
from django.core.cache import cache
from django.conf import settings
from rest_framework.response import Response
import hashlib
import json


def generate_cache_key(view_name, *args, **kwargs):
    """
    Generate a unique cache key based on view name and parameters.
    
    Args:
        view_name: Name of the view/endpoint
        *args: Positional arguments
        **kwargs: Keyword arguments (usually query params)
    
    Returns:
        str: Unique cache key
    """
    # Create a stable string representation
    key_parts = [view_name]
    
    # Add positional args
    key_parts.extend([str(arg) for arg in args])
    
    # Add sorted kwargs to ensure consistent keys
    for k in sorted(kwargs.keys()):
        key_parts.append(f"{k}={kwargs[k]}")
    
    # Join and hash for shorter keys
    key_string = ":".join(key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    return f"{view_name}:{key_hash}"


def cache_response(timeout=None, key_prefix=None):
    """
    Decorator for caching DRF API responses.
    
    Usage:
        @cache_response(timeout=3600, key_prefix='spell_list')
        def list(self, request):
            return super().list(request)
    
    Args:
        timeout: Cache timeout in seconds (None = use default)
        key_prefix: Prefix for cache key (None = use view name)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Generate cache key
            prefix = key_prefix or f"{self.__class__.__name__}.{view_func.__name__}"
            
            # Include query params in cache key
            query_params = dict(request.query_params.items())
            cache_key = generate_cache_key(prefix, *args, **query_params)
            
            # Try to get from cache
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data)
            
            # Execute view function
            response = view_func(self, request, *args, **kwargs)
            
            # Cache successful responses
            if response.status_code == 200:
                cache_timeout = timeout or settings.CACHE_TTL.get('default', 300)
                cache.set(cache_key, response.data, cache_timeout)
            
            return response
        
        return wrapper
    return decorator


def cache_model_instance(model_name, instance_id, data, timeout=None):
    """
    Cache a single model instance.
    
    Args:
        model_name: Model name (e.g., 'Spell', 'Enemy')
        instance_id: Instance primary key
        data: Data to cache
        timeout: Cache timeout in seconds
    """
    cache_key = f"{model_name}:{instance_id}"
    cache_timeout = timeout or settings.CACHE_TTL.get(model_name.lower(), 300)
    cache.set(cache_key, data, cache_timeout)


def get_cached_model_instance(model_name, instance_id):
    """
    Retrieve a cached model instance.
    
    Args:
        model_name: Model name (e.g., 'Spell', 'Enemy')
        instance_id: Instance primary key
    
    Returns:
        Cached data or None if not found
    """
    cache_key = f"{model_name}:{instance_id}"
    return cache.get(cache_key)


def invalidate_cache(pattern):
    """
    Invalidate cache keys matching a pattern.
    
    Args:
        pattern: Pattern to match (e.g., 'Spell:*', 'Character:123:*')
    """
    # Note: This requires Redis and access to delete_pattern
    try:
        cache.delete_pattern(pattern)
    except AttributeError:
        # Fallback: just clear the whole cache
        cache.clear()


def invalidate_model_cache(model_name, instance_id=None):
    """
    Invalidate cache for a specific model or instance.
    
    Args:
        model_name: Model name (e.g., 'Spell', 'Enemy')
        instance_id: Optional instance ID (if None, clears all for model)
    """
    if instance_id:
        pattern = f"{model_name}:{instance_id}*"
    else:
        pattern = f"{model_name}:*"
    
    invalidate_cache(pattern)


class CacheInvalidationMixin:
    """
    Mixin for ViewSets to automatically invalidate cache on updates.
    
    Usage:
        class SpellViewSet(CacheInvalidationMixin, viewsets.ReadOnlyModelViewSet):
            cache_model_name = 'Spell'
    """
    cache_model_name = None
    
    def perform_create(self, serializer):
        """Invalidate cache after creating an instance"""
        super().perform_create(serializer)
        if self.cache_model_name:
            invalidate_model_cache(self.cache_model_name)
    
    def perform_update(self, serializer):
        """Invalidate cache after updating an instance"""
        instance = serializer.instance
        super().perform_update(serializer)
        if self.cache_model_name:
            invalidate_model_cache(self.cache_model_name, instance.pk)
    
    def perform_destroy(self, instance):
        """Invalidate cache after deleting an instance"""
        instance_id = instance.pk
        super().perform_destroy(instance)
        if self.cache_model_name:
            invalidate_model_cache(self.cache_model_name, instance_id)
