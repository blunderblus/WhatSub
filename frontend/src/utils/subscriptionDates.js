export function formatDateInput(date) {
  return date.toISOString().slice(0, 10);
}

function addMonths(date, months) {
  const next = new Date(date);
  const day = next.getDate();
  next.setDate(1);
  next.setMonth(next.getMonth() + months);
  const lastDay = new Date(next.getFullYear(), next.getMonth() + 1, 0).getDate();
  next.setDate(Math.min(day, lastDay));
  return next;
}

export function renewalDateFrom(startDate, billingPeriod) {
  const next = new Date(startDate);
  if (billingPeriod === 'weekly') {
    next.setDate(next.getDate() + 7);
    return next;
  }
  if (billingPeriod === 'annual') {
    return addMonths(next, 12);
  }
  return addMonths(next, 1);
}
