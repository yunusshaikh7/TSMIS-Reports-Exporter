"""California state route list + free-text route parsing (P8a leaf).

Extracted verbatim from `common.py`. Pure (stdlib `re` only), no Playwright, no
auth, no site state — the canonical route inventory and the loose-input parser
the console flow and the GUI both validate against. `common.py` re-exports
`ROUTES` / `normalize_route` / `parse_routes`, so every caller's
`from common import ROUTES` is unchanged.
"""
import re

ROUTES = [
    "001","002","003","004","005","005S","006","007","008","008U","009","010","010S",
    "011","012","013","014","014U","015","015S","016","017","018","020","022","023",
    "024","025","026","027","028","029","032","033","034","035","036","037","038",
    "039","040","041","043","044","045","046","047","049","050","051","052","053",
    "054","055","056","057","058","058U","059","060","061","062","063","065","066",
    "067","068","070","071","072","073","074","075","076","077","078","079","080",
    "082","083","084","085","086","087","088","089","090","091","092","094","095",
    "096","097","098","099","101","101U","103","104","105","107","108","109","110",
    "111","112","113","114","115","116","118","119","120","121","123","124","125",
    "126","127","128","129","130","131","132","133","134","135","136","137","138",
    "139","140","142","144","145","146","147","149","150","151","152","153","154",
    "155","156","158","160","161","162","163","164","165","166","167","168","169",
    "170","172","173","174","175","177","178","178S","180","182","183","184","185",
    "186","187","188","189","190","191","192","193","197","198","199","200","201",
    "202","203","204","205","207","210","210U","211","213","215","216","217","218",
    "219","220","221","222","223","227","229","232","233","236","237","238","241",
    "242","243","244","245","246","247","253","254","255","259","260","261","262",
    "263","265","266","267","269","270","271","273","275","280","281","282","283",
    "284","299","330","371","380","395","405","505","580","605","680","710","780",
    "805","880","880S","905","980",
]

_ROUTES_SET = set(ROUTES)


def normalize_route(token):
    """Normalize one user-typed route token to its canonical ROUTES form.

    Accepts loose input -- any casing or zero-padding, with an optional letter
    suffix -- so '5', '05', '005', '5s', and '005S' all map to their canonical
    spelling ('005', '005S'). Returns the canonical route string if it matches a
    known route, else None.
    """
    t = token.strip().upper()
    m = re.fullmatch(r"(\d+)([A-Z]*)", t)
    if not m:
        return None
    digits, suffix = m.groups()
    candidate = f"{int(digits):03d}{suffix}"
    return candidate if candidate in _ROUTES_SET else None


def parse_routes(text):
    """Parse free-text into a validated route list in canonical ROUTES order.

    Routes may be separated by commas, spaces, semicolons, or newlines, in any
    casing or zero-padding ('5', '005', '5s', '005S'). Returns the matched
    routes de-duplicated and ordered as in ROUTES (so export order stays stable
    regardless of how the user typed them).

    Raises ValueError -- with a user-safe, UI-neutral message -- if no routes
    were given or if any token doesn't match a known route. Callers decide
    whether "no input" should instead mean "all routes" before calling this.
    """
    tokens = [t for t in re.split(r"[\s,;]+", text.strip()) if t]
    if not tokens:
        raise ValueError("No routes entered.")
    chosen, unknown = set(), []
    for tok in tokens:
        norm = normalize_route(tok)
        if norm is None:
            unknown.append(tok)
        else:
            chosen.add(norm)
    if unknown:
        raise ValueError("Not valid route(s): " + ", ".join(unknown))
    return [r for r in ROUTES if r in chosen]
