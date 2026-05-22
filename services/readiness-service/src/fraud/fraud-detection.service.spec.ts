import { describe, expect, it } from 'vitest';
import { FraudDetectionService } from './fraud-detection.service.js';

describe('FraudDetectionService', () => {
  const svc = new FraudDetectionService();

  it('returns GREEN for clean text', () => {
    const r = svc.scan('buyer-x', 'We would like to order 500 units, paid via LC at sight.');
    expect(r.riskLevel).toBe('GREEN');
    expect(r.flags).toHaveLength(0);
  });

  it('flags OFFSHORE_PAYMENT as CRITICAL', () => {
    const r = svc.scan(
      'buyer-x',
      'Please send invoice but route payment to our offshore account in Mauritius.',
    );
    expect(r.flags.some((f) => f.id === 'OFFSHORE_PAYMENT')).toBe(true);
    expect(r.riskLevel).toBe('CRITICAL');
  });

  it('flags INVOICE_MANIPULATION as CRITICAL', () => {
    const r = svc.scan(
      'buyer-x',
      'Can you under-invoice the shipment to reduce customs on our side?',
    );
    expect(r.flags.some((f) => f.id === 'INVOICE_MANIPULATION')).toBe(true);
    expect(r.riskLevel).toBe('CRITICAL');
  });
});