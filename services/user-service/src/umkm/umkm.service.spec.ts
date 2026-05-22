import { describe, expect, it, vi } from 'vitest';
import { UmkmService } from './umkm.service.js';

describe('UmkmService', () => {
  it('rejects duplicate NIB', async () => {
    const db = {
      query: { umkm: { findFirst: vi.fn().mockResolvedValue({ id: 'x' }) } },
    } as any;
    const producer = { dispatchVerification: vi.fn() } as any;
    const svc = new UmkmService(db, producer);
    await expect(
      svc.create({ legalName: 'X', nib: '1234567890123' }, 'u1'),
    ).rejects.toThrow(/sudah terdaftar/);
    expect(producer.dispatchVerification).not.toHaveBeenCalled();
  });
});