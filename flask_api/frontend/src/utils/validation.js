export function validatePeriod(period) {
  const validPeriods = ['daily', 'weekly', 'monthly'];
  if (!validPeriods.includes(period)) {
    return { valid: false, error: `Invalid period. Must be one of: ${validPeriods.join(', ')}` };
  }
  return { valid: true };
}

export function validateDays(days) {
  if (typeof days !== 'number' || days < 1 || days > 365) {
    return { valid: false, error: 'Days must be a number between 1 and 365' };
  }
  return { valid: true };
}

export function validateLimit(limit) {
  if (typeof limit !== 'number' || limit < 1 || limit > 100) {
    return { valid: false, error: 'Limit must be a number between 1 and 100' };
  }
  return { valid: true };
}

export function validateChartType(chartType) {
  const validTypes = [
    'messages_per_day',
    'users_per_day',
    'conversations_per_day',
    'messages_by_hour',
    'message_type_distribution',
  ];
  if (!validTypes.includes(chartType)) {
    return { valid: false, error: `Invalid chart type. Must be one of: ${validTypes.join(', ')}` };
  }
  return { valid: true };
}

export function validateMetricResponse(data) {
  const requiredFields = ['id', 'label', 'value'];
  for (const field of requiredFields) {
    if (!(field in data)) {
      return { valid: false, error: `Missing required field: ${field}` };
    }
  }
  return { valid: true };
}

export function validateChartData(data) {
  if (!Array.isArray(data)) {
    return { valid: false, error: 'Chart data must be an array' };
  }
  for (const point of data) {
    if (!('label' in point) || !('value' in point)) {
      return { valid: false, error: 'Each data point must have label and value' };
    }
  }
  return { valid: true };
}

export function validateUser(user) {
  const requiredFields = ['id', 'username', 'email'];
  for (const field of requiredFields) {
    if (!(field in user)) {
      return { valid: false, error: `Missing required field: ${field}` };
    }
  }
  return { valid: true };
}

export function validateConversation(conversation) {
  const requiredFields = ['id', 'name'];
  for (const field of requiredFields) {
    if (!(field in conversation)) {
      return { valid: false, error: `Missing required field: ${field}` };
    }
  }
  return { valid: true };
}
