import { ConflictException, ForbiddenException, Inject, Injectable, NotFoundException } from '@nestjs/common';
import { eq } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import { products, umkm, type Umkm } from '../database/schema/index.js';
import { VerificationProducer } from '../queue/verification.producer.js';
import type { CreateUmkmDto } from './dto/create-umkm.dto.js';

@Injectable()
export class UmkmService {
  constructor(
    @Inject(DRIZZLE) private readonly db: DrizzleDB,
    private readonly verificationProducer: VerificationProducer,
  ) {}

  async create(dto: CreateUmkmDto, userId: string): Promise<Umkm> {
    const existing = await this.db.query.umkm.findFirst({ where: eq(umkm.nib, dto.nib) });
    if (existing) {
      throw new ConflictException(`NIB ${dto.nib} sudah terdaftar`);
    }

    const [created] = await this.db
      .insert(umkm)
      .values({
        legalName: dto.legalName,
        nib: dto.nib,
        description: dto.description,
        userId,
      })
      .returning();

    if (!created) throw new Error('Failed to create UMKM');

    await this.verificationProducer.dispatchVerification({
      umkmId: created.id,
      nib: created.nib,
      userId,
    });

    return created;
  }

  async findByUser(userId: string): Promise<Umkm | null> {
    const row = await this.db.query.umkm.findFirst({ where: eq(umkm.userId, userId) });
    return row ?? null;
  }

  async findById(id: string): Promise<Umkm> {
    const row = await this.db.query.umkm.findFirst({ where: eq(umkm.id, id) });
    if (!row) throw new NotFoundException(`UMKM ${id} not found`);
    return row;
  }

  /** Composite export-readiness score (M2), computed from profile + products. */
  async readiness(umkmId: string, userId: string) {
    const row = await this.findById(umkmId);
    if (row.userId !== userId) throw new ForbiddenException('Not your UMKM');
    const prods = await this.db.select().from(products).where(eq(products.umkmId, umkmId));

    const identity = row.nib && row.legalName ? 40 : 20;
    const verification =
      row.verificationStatus === 'VERIFIED' ? 30 : row.verificationStatus === 'FAILED' ? 0 : 15;
    const productScore = prods.length > 0 ? 30 : 0;
    const score = identity + verification + productScore;
    const level = score >= 80 ? 'ready' : score >= 50 ? 'partial' : 'not_ready';

    return {
      umkmId,
      score,
      level,
      breakdown: [
        { label: 'Kelengkapan Identitas', value: identity, weight: 40 },
        { label: 'Status Verifikasi', value: verification, weight: 30 },
        { label: 'Kelengkapan Produk', value: productScore, weight: 30 },
      ],
    };
  }

  async update(
    id: string,
    dto: { legalName?: string; description?: string },
    userId: string,
  ): Promise<Umkm> {
    const existing = await this.findById(id);
    if (existing.userId !== userId) throw new ForbiddenException('Not your UMKM');
    const [updated] = await this.db
      .update(umkm)
      .set({
        ...(dto.legalName !== undefined ? { legalName: dto.legalName } : {}),
        ...(dto.description !== undefined ? { description: dto.description } : {}),
        updatedAt: new Date(),
      })
      .where(eq(umkm.id, id))
      .returning();
    if (!updated) throw new NotFoundException(`UMKM ${id} not found`);
    return updated;
  }
}