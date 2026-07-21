import { ConflictException, Inject, Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcrypt';
import { eq } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import { users } from '../database/schema/index.js';

export interface AuthResult {
  accessToken: string;
  refreshToken: string;
  user: { id: string; email: string; tier: string };
}

@Injectable()
export class AuthService {
  constructor(
    @Inject(DRIZZLE) private readonly db: DrizzleDB,
    private readonly jwt: JwtService,
    private readonly config: ConfigService,
  ) {}

  async register(email: string, password: string): Promise<AuthResult> {
    const existing = await this.db.query.users.findFirst({ where: eq(users.email, email) });
    if (existing) throw new ConflictException('Email already registered');

    const passwordHash = await bcrypt.hash(password, 12);
    const [created] = await this.db
      .insert(users)
      .values({ email, passwordHash })
      .returning();
    if (!created) throw new Error('Failed to create user');

    return this.issueTokens(created.id, created.email, created.tier);
  }

  async login(email: string, password: string): Promise<AuthResult> {
    const user = await this.db.query.users.findFirst({ where: eq(users.email, email) });
    if (!user || !user.isActive) throw new UnauthorizedException('Invalid credentials');

    const valid = await bcrypt.compare(password, user.passwordHash);
    if (!valid) throw new UnauthorizedException('Invalid credentials');

    return this.issueTokens(user.id, user.email, user.tier);
  }

  /**
   * Exchange a valid refresh token for a fresh access+refresh pair (rotation).
   * Reuses the existing JWT mechanism — the refresh token is a longer-lived JWT
   * signed with the same secret. Rejects if invalid/expired or the user is gone.
   */
  async refresh(refreshToken: string): Promise<AuthResult> {
    let payload: { sub: string; email: string; tier: string };
    try {
      payload = await this.jwt.verifyAsync(refreshToken);
    } catch {
      throw new UnauthorizedException('Invalid or expired refresh token');
    }
    const user = await this.db.query.users.findFirst({ where: eq(users.id, payload.sub) });
    if (!user || !user.isActive) throw new UnauthorizedException('User not found or inactive');
    return this.issueTokens(user.id, user.email, user.tier);
  }

  private async issueTokens(userId: string, email: string, tier: string): Promise<AuthResult> {
    const payload = { sub: userId, email, tier };
    const accessToken = await this.jwt.signAsync(payload);
    const refreshToken = await this.jwt.signAsync(payload, {
      expiresIn: this.config.get<string>('JWT_REFRESH_TOKEN_EXPIRES') ?? '14d',
    });
    return { accessToken, refreshToken, user: { id: userId, email, tier } };
  }
}