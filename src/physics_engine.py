"""
AZAN Physics Engine — Phase 6b
Solves classical physics problems symbolically using sympy.

Domains: kinematics, forces, energy, electromagnetism,
         thermodynamics, waves/optics, unit conversion.
"""

import logging
import re
from typing import Dict, Any, Optional
import sympy as sp
from sympy import symbols, solve, sqrt, pi, Rational, Abs, oo

logger = logging.getLogger(__name__)

# ── Physical Constants ──────────────────────────────────────────────────────
CONSTANTS = {
    "g":       9.81,          # m/s² gravitational acceleration
    "G":       6.674e-11,     # N⋅m²/kg² gravitational constant
    "c":       3e8,           # m/s speed of light
    "k_e":     8.988e9,       # N⋅m²/C² Coulomb's constant
    "epsilon0": 8.854e-12,    # F/m permittivity of free space
    "mu0":     1.257e-6,      # H/m permeability of free space
    "h":       6.626e-34,     # J⋅s Planck's constant
    "k_b":     1.381e-23,     # J/K Boltzmann constant
    "R":       8.314,         # J/(mol⋅K) gas constant
    "e":       1.602e-19,     # C elementary charge
    "m_e":     9.109e-31,     # kg electron mass
    "m_p":     1.673e-27,     # kg proton mass
    "sigma":   5.670e-8,      # W/(m²⋅K⁴) Stefan–Boltzmann constant
    "N_A":     6.022e23,      # 1/mol Avogadro's number
}

# ── Unit Conversion Table ───────────────────────────────────────────────────
_CONVERSIONS = {
    ("meters", "feet"):       3.28084,
    ("feet", "meters"):       1 / 3.28084,
    ("km", "miles"):          0.621371,
    ("miles", "km"):          1 / 0.621371,
    ("kg", "pounds"):         2.20462,
    ("pounds", "kg"):         1 / 2.20462,
    ("celsius", "fahrenheit"): None,  # special
    ("fahrenheit", "celsius"): None,  # special
    ("celsius", "kelvin"):    None,   # special
    ("kelvin", "celsius"):    None,   # special
    ("joules", "calories"):   0.239006,
    ("calories", "joules"):   4.184,
    ("watts", "horsepower"):  1 / 745.7,
    ("horsepower", "watts"):  745.7,
    ("meters", "cm"):         100,
    ("cm", "meters"):         0.01,
    ("meters", "inches"):     39.3701,
    ("inches", "meters"):     0.0254,
    ("liters", "gallons"):    0.264172,
    ("gallons", "liters"):    3.78541,
    ("atm", "pascals"):       101325,
    ("pascals", "atm"):       1 / 101325,
}


class PhysicsEngine:
    """
    Symbolic physics problem solver for AZAN.
    """

    def __init__(self):
        self.history = []

    def solve(self, problem: str, domain: str = "auto") -> Dict[str, Any]:
        """
        Solve a physics problem.

        Args:
            problem: Natural language physics problem
            domain: kinematics, forces, energy, em, thermo, waves,
                    unit_convert, constants, auto

        Returns:
            Dict with result, steps, and domain info
        """
        if domain == "auto":
            domain = self._detect_domain(problem)

        try:
            if domain == "kinematics":
                return self._kinematics(problem)
            elif domain == "forces":
                return self._forces(problem)
            elif domain == "energy":
                return self._energy(problem)
            elif domain == "em":
                return self._electromagnetism(problem)
            elif domain == "thermo":
                return self._thermodynamics(problem)
            elif domain == "waves":
                return self._waves(problem)
            elif domain == "unit_convert":
                return self._unit_convert(problem)
            elif domain == "constants":
                return self._get_constants(problem)
            else:
                return {"success": False, "error": f"Unknown physics domain: {domain}"}
        except Exception as e:
            logger.error(f"Physics engine error: {e}")
            return {"success": False, "error": str(e), "domain": domain}

    # ── Domain Detection ────────────────────────────────────────────────────
    def _detect_domain(self, text: str) -> str:
        lower = text.lower()
        domain_keywords = {
            "unit_convert": ["convert", "to feet", "to meters", "to celsius", "to fahrenheit", "to kelvin", "to miles", "to km", "to pounds", "to kg"],
            "constants":    ["constant", "speed of light", "planck", "boltzmann", "avogadro"],
            "kinematics":   ["velocity", "speed", "acceleration", "distance", "displacement", "projectile", "v=", "u=", "s=", "free fall", "motion"],
            "forces":       ["force", "f=ma", "newton", "friction", "tension", "normal", "incline", "weight", "mass", "f="],
            "energy":       ["energy", "kinetic", "potential", "work", "power", "joule", "conservation", "ke", "pe"],
            "em":           ["coulomb", "charge", "electric", "magnetic", "ohm", "voltage", "current", "resistance", "capacit", "field"],
            "thermo":       ["temperature", "heat", "entropy", "gas law", "ideal gas", "pv=nrt", "pressure", "volume", "moles", "thermal"],
            "waves":        ["wave", "frequency", "wavelength", "snell", "refraction", "diffraction", "optics", "hertz", "period"],
        }
        for domain, kws in domain_keywords.items():
            for kw in kws:
                if kw in lower:
                    return domain
        return "kinematics"  # default

    # ── Kinematics ──────────────────────────────────────────────────────────
    def _kinematics(self, problem: str) -> Dict[str, Any]:
        steps = []
        vals = self._extract_values(problem)
        u_val = vals.get('u')  # initial velocity
        v_val = vals.get('v')  # final velocity
        a_val = vals.get('a')  # acceleration
        t_val = vals.get('t')  # time
        s_val = vals.get('s')  # displacement

        u_sym, v_sym, a_sym, t_sym, s_sym = symbols('u v a t s')

        # SUVAT equations
        eqs = [
            sp.Eq(v_sym, u_sym + a_sym * t_sym),          # v = u + at
            sp.Eq(s_sym, u_sym * t_sym + Rational(1, 2) * a_sym * t_sym**2),  # s = ut + ½at²
            sp.Eq(v_sym**2, u_sym**2 + 2 * a_sym * s_sym),  # v² = u² + 2as
        ]

        known = {}
        unknowns = []
        var_map = {'u': u_sym, 'v': v_sym, 'a': a_sym, 't': t_sym, 's': s_sym}

        for name, sym in var_map.items():
            if vals.get(name) is not None:
                known[sym] = float(vals[name])
            else:
                unknowns.append(sym)

        steps.append(f"Known: {', '.join(f'{k}={v}' for k, v in known.items())}")
        steps.append(f"Unknowns: {', '.join(str(u) for u in unknowns)}")

        # Substitute known values and solve each unknown
        results = {}
        for eq in eqs:
            sub_eq = eq.subs(known)
            for unk in unknowns:
                if str(unk) in results:
                    continue  # already solved
                # Only solve if this is the sole free symbol (concrete answer)
                free = sub_eq.free_symbols
                if unk in free and len(free) == 1:
                    try:
                        sol = solve(sub_eq, unk)
                        real_sols = [float(s) for s in sol if s.is_real]
                        if real_sols:
                            val = round(real_sols[0], 6)
                            results[str(unk)] = val
                            known[unk] = val  # feed forward
                            steps.append(f"From {eq}: {unk} = {val}")
                    except:
                        pass

        if not results:
            return {"success": False, "error": "Not enough information to solve. Provide at least 3 of: u, v, a, t, s"}

        # Add units
        units = {'u': 'm/s', 'v': 'm/s', 'a': 'm/s²', 't': 's', 's': 'm'}
        result_str = "; ".join(f"{k} = {v} {units.get(k, '')}" for k, v in results.items())

        return {
            "success": True,
            "result": result_str,
            "data": results,
            "steps": steps,
            "domain": "kinematics",
        }


    # ── Forces ──────────────────────────────────────────────────────────────
    def _forces(self, problem: str) -> Dict[str, Any]:
        steps = []
        vals = self._extract_values(problem)
        F_val = vals.get('f') or vals.get('force')
        m_val = vals.get('m') or vals.get('mass')
        a_val = vals.get('a') or vals.get('acceleration')
        mu_val = vals.get('mu') or vals.get('friction')

        F_sym, m_sym, a_sym = symbols('F m a', positive=True)
        g_val = CONSTANTS["g"]

        results = {}

        # F = ma
        if F_val is not None and m_val is not None:
            a_result = float(F_val) / float(m_val)
            results['acceleration'] = round(a_result, 4)
            steps.append(f"F = ma → a = F/m = {F_val}/{m_val} = {a_result} m/s²")
        elif m_val is not None and a_val is not None:
            f_result = float(m_val) * float(a_val)
            results['force'] = round(f_result, 4)
            steps.append(f"F = ma = {m_val}×{a_val} = {f_result} N")
        elif F_val is not None and a_val is not None:
            m_result = float(F_val) / float(a_val)
            results['mass'] = round(m_result, 4)
            steps.append(f"m = F/a = {F_val}/{a_val} = {m_result} kg")

        # Weight
        if m_val is not None:
            weight = float(m_val) * g_val
            results['weight'] = round(weight, 4)
            steps.append(f"Weight = mg = {m_val}×{g_val} = {weight} N")

        # Friction
        if mu_val is not None and m_val is not None:
            normal = float(m_val) * g_val
            friction = float(mu_val) * normal
            results['friction_force'] = round(friction, 4)
            steps.append(f"Friction = μN = {mu_val}×{normal} = {friction} N")

        if not results:
            return {"success": False, "error": "Provide values for F (force), m (mass), a (acceleration)"}

        return {
            "success": True,
            "result": "; ".join(f"{k} = {v}" for k, v in results.items()),
            "data": results,
            "steps": steps,
            "domain": "forces",
        }

    # ── Energy ──────────────────────────────────────────────────────────────
    def _energy(self, problem: str) -> Dict[str, Any]:
        steps = []
        vals = self._extract_values(problem)
        m_val = vals.get('m') or vals.get('mass')
        v_val = vals.get('v') or vals.get('velocity') or vals.get('speed')
        h_val = vals.get('h') or vals.get('height')
        g_val = CONSTANTS["g"]

        results = {}

        if m_val is not None and v_val is not None:
            ke = 0.5 * float(m_val) * float(v_val)**2
            results['kinetic_energy'] = round(ke, 4)
            steps.append(f"KE = ½mv² = 0.5×{m_val}×{v_val}² = {ke} J")

        if m_val is not None and h_val is not None:
            pe = float(m_val) * g_val * float(h_val)
            results['potential_energy'] = round(pe, 4)
            steps.append(f"PE = mgh = {m_val}×{g_val}×{h_val} = {pe} J")

        if 'kinetic_energy' in results and 'potential_energy' in results:
            total = results['kinetic_energy'] + results['potential_energy']
            results['total_mechanical_energy'] = round(total, 4)
            steps.append(f"Total E = KE + PE = {total} J")

        if not results:
            return {"success": False, "error": "Provide m (mass) and v (velocity) or h (height)"}

        return {
            "success": True,
            "result": "; ".join(f"{k} = {v}" for k, v in results.items()),
            "data": results,
            "steps": steps,
            "domain": "energy",
        }

    # ── Electromagnetism ────────────────────────────────────────────────────
    def _electromagnetism(self, problem: str) -> Dict[str, Any]:
        steps = []
        vals = self._extract_values(problem)
        results = {}

        # Coulomb's Law: F = k * q1 * q2 / r²
        q1 = vals.get('q1') or vals.get('charge1')
        q2 = vals.get('q2') or vals.get('charge2')
        r_val = vals.get('r') or vals.get('distance')
        V_val = vals.get('v') or vals.get('voltage')
        I_val = vals.get('i') or vals.get('current')
        R_val = vals.get('r_ohm') or vals.get('resistance')

        if q1 is not None and q2 is not None and r_val is not None:
            k_e = CONSTANTS["k_e"]
            force = k_e * abs(float(q1)) * abs(float(q2)) / float(r_val)**2
            results['coulomb_force'] = force
            steps.append(f"F = k·|q₁||q₂|/r² = {k_e:.3e}×{q1}×{q2}/{r_val}² = {force:.4e} N")

        # Ohm's Law: V = IR
        if V_val is not None and R_val is not None:
            current = float(V_val) / float(R_val)
            results['current'] = round(current, 6)
            steps.append(f"I = V/R = {V_val}/{R_val} = {current} A")
        elif V_val is not None and I_val is not None:
            resistance = float(V_val) / float(I_val)
            results['resistance'] = round(resistance, 4)
            steps.append(f"R = V/I = {V_val}/{I_val} = {resistance} Ω")
        elif I_val is not None and R_val is not None:
            voltage = float(I_val) * float(R_val)
            results['voltage'] = round(voltage, 4)
            steps.append(f"V = IR = {I_val}×{R_val} = {voltage} V")

        if not results:
            return {"success": False, "error": "Provide charge/distance for Coulomb or V/I/R for Ohm's law"}

        return {
            "success": True,
            "result": "; ".join(f"{k} = {v}" for k, v in results.items()),
            "data": results,
            "steps": steps,
            "domain": "em",
        }

    # ── Thermodynamics ──────────────────────────────────────────────────────
    def _thermodynamics(self, problem: str) -> Dict[str, Any]:
        steps = []
        vals = self._extract_values(problem)
        results = {}

        P = vals.get('p') or vals.get('pressure')
        V = vals.get('v_vol') or vals.get('volume')
        n = vals.get('n') or vals.get('moles')
        T = vals.get('t_temp') or vals.get('temperature')
        R_gas = CONSTANTS["R"]

        # PV = nRT
        known_count = sum(1 for v in [P, V, n, T] if v is not None)
        if known_count >= 3:
            if P is None:
                P_res = float(n) * R_gas * float(T) / float(V)
                results['pressure'] = round(P_res, 4)
                steps.append(f"P = nRT/V = {n}×{R_gas}×{T}/{V} = {P_res} Pa")
            elif V is None:
                V_res = float(n) * R_gas * float(T) / float(P)
                results['volume'] = round(V_res, 6)
                steps.append(f"V = nRT/P = {n}×{R_gas}×{T}/{P} = {V_res} m³")
            elif n is None:
                n_res = float(P) * float(V) / (R_gas * float(T))
                results['moles'] = round(n_res, 6)
                steps.append(f"n = PV/RT = {P}×{V}/({R_gas}×{T}) = {n_res} mol")
            elif T is None:
                T_res = float(P) * float(V) / (float(n) * R_gas)
                results['temperature'] = round(T_res, 4)
                steps.append(f"T = PV/nR = {P}×{V}/({n}×{R_gas}) = {T_res} K")

        if not results:
            return {"success": False, "error": "Provide 3 of: P (pressure), V (volume), n (moles), T (temperature) for ideal gas law"}

        return {
            "success": True,
            "result": "; ".join(f"{k} = {v}" for k, v in results.items()),
            "data": results,
            "steps": steps,
            "domain": "thermo",
        }

    # ── Waves & Optics ──────────────────────────────────────────────────────
    def _waves(self, problem: str) -> Dict[str, Any]:
        steps = []
        vals = self._extract_values(problem)
        results = {}

        freq = vals.get('f') or vals.get('frequency')
        wl = vals.get('lambda') or vals.get('wavelength')
        v_wave = vals.get('v') or vals.get('speed')

        # v = fλ
        if freq is not None and wl is not None:
            speed = float(freq) * float(wl)
            results['wave_speed'] = round(speed, 4)
            steps.append(f"v = fλ = {freq}×{wl} = {speed} m/s")
        elif v_wave is not None and freq is not None:
            wavelength = float(v_wave) / float(freq)
            results['wavelength'] = wavelength
            steps.append(f"λ = v/f = {v_wave}/{freq} = {wavelength} m")
        elif v_wave is not None and wl is not None:
            frequency = float(v_wave) / float(wl)
            results['frequency'] = frequency
            steps.append(f"f = v/λ = {v_wave}/{wl} = {frequency} Hz")

        # Period
        if freq is not None:
            period = 1 / float(freq)
            results['period'] = period
            steps.append(f"T = 1/f = 1/{freq} = {period} s")

        # Snell's Law: n1*sin(θ1) = n2*sin(θ2)
        n1 = vals.get('n1')
        n2 = vals.get('n2')
        theta1 = vals.get('theta1') or vals.get('angle1')
        if n1 is not None and n2 is not None and theta1 is not None:
            import math
            sin_theta2 = float(n1) * math.sin(math.radians(float(theta1))) / float(n2)
            if abs(sin_theta2) <= 1:
                theta2 = math.degrees(math.asin(sin_theta2))
                results['refracted_angle'] = round(theta2, 4)
                steps.append(f"Snell's Law: θ₂ = arcsin(n₁sin(θ₁)/n₂) = {theta2}°")

        if not results:
            return {"success": False, "error": "Provide f (frequency) and λ (wavelength) or v (wave speed)"}

        return {
            "success": True,
            "result": "; ".join(f"{k} = {v}" for k, v in results.items()),
            "data": results,
            "steps": steps,
            "domain": "waves",
        }

    # ── Unit Conversion ─────────────────────────────────────────────────────
    def _unit_convert(self, problem: str) -> Dict[str, Any]:
        # Parse: "5 meters to feet" or "100 celsius to fahrenheit"
        m = re.search(r'([\d.]+)\s+(\w+)\s+to\s+(\w+)', problem, re.IGNORECASE)
        if not m:
            return {"success": False, "error": "Format: '[value] [from_unit] to [to_unit]'"}

        value = float(m.group(1))
        from_u = m.group(2).lower()
        to_u = m.group(3).lower()

        # Temperature special cases
        if from_u == "celsius" and to_u == "fahrenheit":
            result = value * 9 / 5 + 32
        elif from_u == "fahrenheit" and to_u == "celsius":
            result = (value - 32) * 5 / 9
        elif from_u == "celsius" and to_u == "kelvin":
            result = value + 273.15
        elif from_u == "kelvin" and to_u == "celsius":
            result = value - 273.15
        else:
            factor = _CONVERSIONS.get((from_u, to_u))
            if factor is None:
                return {"success": False, "error": f"Unknown conversion: {from_u} → {to_u}"}
            result = value * factor

        return {
            "success": True,
            "result": f"{value} {from_u} = {round(result, 6)} {to_u}",
            "data": {"value": value, "from": from_u, "to": to_u, "converted": round(result, 6)},
            "steps": [f"{value} {from_u} → {round(result, 6)} {to_u}"],
            "domain": "unit_convert",
        }

    # ── Constants Lookup ────────────────────────────────────────────────────
    def _get_constants(self, problem: str) -> Dict[str, Any]:
        lower = problem.lower()
        matches = {}
        friendly = {
            "g": "Gravitational acceleration (g) = 9.81 m/s²",
            "G": "Gravitational constant (G) = 6.674×10⁻¹¹ N⋅m²/kg²",
            "c": "Speed of light (c) = 3×10⁸ m/s",
            "k_e": "Coulomb's constant (kₑ) = 8.988×10⁹ N⋅m²/C²",
            "h": "Planck's constant (h) = 6.626×10⁻³⁴ J⋅s",
            "k_b": "Boltzmann constant (kB) = 1.381×10⁻²³ J/K",
            "R": "Gas constant (R) = 8.314 J/(mol⋅K)",
            "e": "Elementary charge (e) = 1.602×10⁻¹⁹ C",
            "N_A": "Avogadro's number (Nₐ) = 6.022×10²³ /mol",
            "sigma": "Stefan–Boltzmann (σ) = 5.670×10⁻⁸ W/(m²⋅K⁴)",
        }
        for key, desc in friendly.items():
            if key.lower() in lower or any(w in lower for w in desc.lower().split()):
                matches[key] = {"value": CONSTANTS[key], "description": desc}

        if not matches:
            # Return all constants
            matches = {k: {"value": v, "description": friendly.get(k, "")} for k, v in CONSTANTS.items() if k in friendly}

        return {
            "success": True,
            "result": "\n".join(v["description"] for v in matches.values()),
            "data": matches,
            "steps": ["Physical constants lookup"],
            "domain": "constants",
        }

    # ── Value Extractor ─────────────────────────────────────────────────────
    def _extract_values(self, text: str) -> Dict[str, Optional[float]]:
        """Extract variable=value pairs from natural language."""
        vals = {}
        # Alias map: verbose names → short SUVAT/physics names
        aliases = {
            'velocity': 'v', 'speed': 'v', 'final_velocity': 'v',
            'initial_velocity': 'u', 'initial': 'u',
            'acceleration': 'a', 'accel': 'a',
            'time': 't', 'duration': 't',
            'distance': 's', 'displacement': 's',
            'mass': 'm', 'weight_kg': 'm',
            'force': 'f',
            'height': 'h',
            'frequency': 'f', 'freq': 'f',
            'wavelength': 'lambda',
            'voltage': 'v', 'current': 'i', 'resistance': 'r_ohm',
            'pressure': 'p', 'volume': 'v_vol', 'temperature': 't_temp',
            'moles': 'n',
        }

        # Pattern: "v=20" or "v = 20" or "velocity=20"
        for m in re.finditer(r'(\w+)\s*=\s*([-+]?[\d.]+(?:e[-+]?\d+)?)', text, re.IGNORECASE):
            key = m.group(1).lower()
            # Apply alias
            key = aliases.get(key, key)
            try:
                vals[key] = float(m.group(2))
            except ValueError:
                pass

        # Also try "find X" to know what's unknown
        find_match = re.search(r'find\s+(\w+)', text, re.IGNORECASE)
        if find_match:
            raw = find_match.group(1).lower()
            vals['_find'] = aliases.get(raw, raw)

        return vals



# ── Global singleton ────────────────────────────────────────────────────────
_engine = PhysicsEngine()

def get_physics_engine() -> PhysicsEngine:
    return _engine
