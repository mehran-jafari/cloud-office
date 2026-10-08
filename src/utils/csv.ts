/**
 * سلول امن CSV:
 *  - همیشه گیومه‌گذاری می‌شود (ویرگول/خط جدید داخل متن ستون‌ها را به‌هم نمی‌ریزد)
 *  - مقدار شروع‌شده با = + - @ tab CR با ' خنثی می‌شود تا Excel/Sheets آن را فرمول اجرا نکند (CSV injection)
 */
export function csvCell(value: unknown): string {
  let text = value === null || value === undefined ? '' : String(value);
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
}
