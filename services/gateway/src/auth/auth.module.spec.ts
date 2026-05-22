import { describe, expect, it } from 'vitest';
import { JwtAuthGuard } from './guards/jwt-auth.guard.js';

describe('JwtAuthGuard', () => {
  it('is constructable', () => {
    expect(new JwtAuthGuard()).toBeInstanceOf(JwtAuthGuard);
  });
});