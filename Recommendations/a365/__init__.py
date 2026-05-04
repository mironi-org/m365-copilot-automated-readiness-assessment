"""A365 recommendation module loader and dispatcher."""

import importlib
from pathlib import Path

from Core.module_loader import get_progress_tracker


current_dir = Path(__file__).parent
recommendation_modules = {}

for file_path in current_dir.glob("*.py"):
    if file_path.name != "__init__.py":
        module_name = file_path.stem
        module = importlib.import_module(f"Recommendations.a365.{module_name}")
        recommendation_modules[module_name.upper()] = module.get_recommendation

tracker = get_progress_tracker()
if getattr(tracker, 'total_services', 0) > 0:
    tracker.update('A365', len(recommendation_modules))


def get_feature_recommendation(feature_name, sku_name, status="Success", client=None):
    """Get recommendation for an A365 package row."""
    module_key = (feature_name or "").upper()
    if module_key in recommendation_modules:
        return recommendation_modules[module_key](sku_name, status, client=client)

    # Fallback to generic package summarization.
    if "CATALOG_PACKAGE" in recommendation_modules:
        return recommendation_modules["CATALOG_PACKAGE"](sku_name, status, client=client)

    raise ValueError(f"Unknown A365 recommendation feature: {feature_name}")