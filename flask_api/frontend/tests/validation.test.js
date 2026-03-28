import { describe, it, expect } from 'vitest';
import {
  validatePeriod,
  validateDays,
  validateLimit,
  validateChartType,
  validateMetricResponse,
  validateChartData,
  validateUser,
  validateConversation,
} from '../src/utils/validation';

describe('Validation Utilities', () => {
  describe('validatePeriod', () => {
    it('should accept daily', () => {
      expect(validatePeriod('daily')).toEqual({ valid: true });
    });

    it('should accept weekly', () => {
      expect(validatePeriod('weekly')).toEqual({ valid: true });
    });

    it('should accept monthly', () => {
      expect(validatePeriod('monthly')).toEqual({ valid: true });
    });

    it('should reject invalid period', () => {
      const result = validatePeriod('invalid');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('Invalid period');
    });
  });

  describe('validateDays', () => {
    it('should accept valid days', () => {
      expect(validateDays(7)).toEqual({ valid: true });
      expect(validateDays(30)).toEqual({ valid: true });
      expect(validateDays(365)).toEqual({ valid: true });
    });

    it('should reject days < 1', () => {
      const result = validateDays(0);
      expect(result.valid).toBe(false);
    });

    it('should reject days > 365', () => {
      const result = validateDays(366);
      expect(result.valid).toBe(false);
    });

    it('should reject non-numbers', () => {
      expect(validateDays('7').valid).toBe(false);
      expect(validateDays(null).valid).toBe(false);
    });
  });

  describe('validateLimit', () => {
    it('should accept valid limits', () => {
      expect(validateLimit(1)).toEqual({ valid: true });
      expect(validateLimit(10)).toEqual({ valid: true });
      expect(validateLimit(100)).toEqual({ valid: true });
    });

    it('should reject limit < 1', () => {
      expect(validateLimit(0).valid).toBe(false);
    });

    it('should reject limit > 100', () => {
      expect(validateLimit(101).valid).toBe(false);
    });
  });

  describe('validateChartType', () => {
    it('should accept valid chart types', () => {
      expect(validateChartType('messages_per_day').valid).toBe(true);
      expect(validateChartType('users_per_day').valid).toBe(true);
      expect(validateChartType('conversations_per_day').valid).toBe(true);
      expect(validateChartType('messages_by_hour').valid).toBe(true);
      expect(validateChartType('message_type_distribution').valid).toBe(true);
    });

    it('should reject invalid chart type', () => {
      const result = validateChartType('invalid');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('Invalid chart type');
    });
  });

  describe('validateMetricResponse', () => {
    it('should accept valid metric data', () => {
      const metric = { id: 'test', label: 'Test', value: 100 };
      expect(validateMetricResponse(metric).valid).toBe(true);
    });

    it('should reject missing id', () => {
      const metric = { label: 'Test', value: 100 };
      expect(validateMetricResponse(metric).valid).toBe(false);
    });

    it('should reject missing label', () => {
      const metric = { id: 'test', value: 100 };
      expect(validateMetricResponse(metric).valid).toBe(false);
    });

    it('should reject missing value', () => {
      const metric = { id: 'test', label: 'Test' };
      expect(validateMetricResponse(metric).valid).toBe(false);
    });
  });

  describe('validateChartData', () => {
    it('should accept valid chart data', () => {
      const data = [
        { label: '2024-01-01', value: 10 },
        { label: '2024-01-02', value: 20 },
      ];
      expect(validateChartData(data).valid).toBe(true);
    });

    it('should reject non-array', () => {
      expect(validateChartData({}).valid).toBe(false);
      expect(validateChartData('invalid').valid).toBe(false);
    });

    it('should reject array with invalid points', () => {
      const data = [
        { label: '2024-01-01', value: 10 },
        { label: '2024-01-02' },
      ];
      expect(validateChartData(data).valid).toBe(false);
    });
  });

  describe('validateUser', () => {
    it('should accept valid user', () => {
      const user = { id: 1, username: 'test', email: 'test@test.com' };
      expect(validateUser(user).valid).toBe(true);
    });

    it('should reject missing required fields', () => {
      expect(validateUser({}).valid).toBe(false);
      expect(validateUser({ id: 1 }).valid).toBe(false);
    });
  });

  describe('validateConversation', () => {
    it('should accept valid conversation', () => {
      const conv = { id: 1, name: 'Test Conversation' };
      expect(validateConversation(conv).valid).toBe(true);
    });

    it('should reject missing required fields', () => {
      expect(validateConversation({}).valid).toBe(false);
      expect(validateConversation({ id: 1 }).valid).toBe(false);
    });
  });
});
