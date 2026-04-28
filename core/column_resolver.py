"""
Safe column value resolver — replaces eval() for column definitions.

Supports two resolution strategies:
  - json_path: dot-separated path into nested dicts/lists, e.g. "product.priceInfo.currentPrice.price"
  - template: simple {variable} or {variable.key} substitution with optional replace operations

Allowed template variables (whitelist):
  product_url, original, prod, idml, current
"""
import json
import re


# ─── json_path resolver ──────────────────────────────────────────────────────

def get_by_path(data_sources: dict, path: str):
    """Traverse nested dict/list by dot-separated path."""
    try:
        parts = path.split('.')
        current = data_sources.get(parts[0])
        for part in parts[1:]:
            if isinstance(current, list):
                # List of {name, value} dicts — look up by name key
                name_map = {
                    item.get("name"): item.get("value")
                    for item in current
                    if isinstance(item, dict)
                }
                current = name_map.get(part, "")
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return ''
        if isinstance(current, (list, dict)):
            return json.dumps(current, ensure_ascii=False)
        return current if current is not None else ''
    except Exception:
        return ''


# ─── template resolver ───────────────────────────────────────────────────────

# Allowed top-level variable names in templates
_ALLOWED_VARS = {'product_url', 'original', 'prod', 'idml', 'current'}

# Matches {variable} or {variable.key} or {variable.key.subkey}
_TEMPLATE_TOKEN_RE = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_.]*)\}')


def _resolve_token(token: str, context: dict) -> str:
    """Resolve a single {variable} or {variable.key} token."""
    parts = token.split('.', 1)
    var_name = parts[0]
    if var_name not in _ALLOWED_VARS:
        return ''
    value = context.get(var_name, '')
    if len(parts) == 2 and isinstance(value, dict):
        value = value.get(parts[1], '')
    return str(value) if value is not None else ''


def resolve_template(template: str, context: dict, replace_ops: list | None = None) -> str:
    """
    Resolve a template string with {variable} placeholders.

    Args:
        template: string like "https://example.com?search={original.UPC}"
        context: dict with allowed variables
        replace_ops: list of [old, new] pairs to apply after substitution
    """
    result = _TEMPLATE_TOKEN_RE.sub(
        lambda m: _resolve_token(m.group(1), context),
        template
    )
    if replace_ops:
        for old, new in replace_ops:
            result = result.replace(old, new)
    return result


# ─── Main entry point ────────────────────────────────────────────────────────

def resolve_column(col_def: dict, context: dict) -> str:
    """
    Resolve a single column value given its definition and context.

    col_def can have:
      - "json_path": dot-separated path (resolved via get_by_path)
      - "template": string with {var} placeholders (resolved via resolve_template)
      - "key_lookup": {"var": "original", "key": "UPC"} — dict key lookup
    """
    if 'template' in col_def:
        return resolve_template(
            col_def['template'],
            context,
            col_def.get('replace')
        )

    if 'key_lookup' in col_def:
        kl = col_def['key_lookup']
        var_name = kl.get('var', '')
        key = kl.get('key', '')
        if var_name not in _ALLOWED_VARS:
            return ''
        obj = context.get(var_name, {})
        if isinstance(obj, dict):
            return str(obj.get(key, ''))
        return ''

    if 'json_path' in col_def:
        return get_by_path(context, col_def['json_path'])

    return ''
