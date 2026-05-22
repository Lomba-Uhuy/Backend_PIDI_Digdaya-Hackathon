import { ConflictException, Inject, Injectable, NotFoundException } from '@nestjs/common';
import { eq } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import { umkm, type Umkm } from '../database/schema/index.js';
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
}