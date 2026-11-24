const stats = {"above": [2616.6737851464727, "m³", 1], "below": [829.9073631364955, "m³", 1], "area": [11741.0, "m²", 0], "coverage": [97.84166666666667, "%", 1]};
for (const [key, [value, unit, digits]] of Object.entries(stats)) {
  const formatted = new Intl.NumberFormat('en-GB', {maximumFractionDigits:digits}).format(value);
  document.querySelector('[data-stat="' + key + '"]').textContent = formatted + (unit === '%' ? unit : ' ' + unit);
}
