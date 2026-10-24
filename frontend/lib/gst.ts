/** Round money to 2 decimal places (string in/out for form fields). */
export function moneyRound(value: number): string {
  if (!Number.isFinite(value)) return "0.00";
  return (Math.round(value * 100) / 100).toFixed(2);
}

export function parseMoney(raw: string): number {
  const n = Number.parseFloat(raw.replace(/,/g, "").trim());
  return Number.isFinite(n) ? n : 0;
}

export function gstBreakdown(taxableRaw: string, gstPercentRaw: string) {
  const taxable = parseMoney(taxableRaw);
  const gstPercent = parseMoney(gstPercentRaw);
  const gst = (taxable * gstPercent) / 100;
  const total = taxable + gst;
  return {
    taxable: moneyRound(taxable),
    gstPercent: moneyRound(gstPercent),
    gst: moneyRound(gst),
    total: moneyRound(total),
  };
}
