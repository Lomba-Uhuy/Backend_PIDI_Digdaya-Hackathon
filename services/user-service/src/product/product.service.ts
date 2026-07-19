import { BadRequestException, ForbiddenException, Inject, Injectable, NotFoundException } from '@nestjs/common';
import { eq } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import { products, type Product } from '../database/schema/index.js';
import { UmkmService } from '../umkm/umkm.service.js';
import { VerificationProducer } from '../queue/verification.producer.js';
import type { CreateProductDto } from './dto/create-product.dto.js';

@Injectable()
export class ProductService {
  constructor(
    @Inject(DRIZZLE) private readonly db: DrizzleDB,
    private readonly umkmService: UmkmService,
    private readonly verificationProducer: VerificationProducer,
  ) {}

  async create(umkmId: string, dto: CreateProductDto, userId: string): Promise<Product> {
    const umkm = await this.umkmService.findById(umkmId);
    if (umkm.userId !== userId) {
      throw new ForbiddenException('Not your UMKM');
    }
    if (dto.priceMax < dto.priceMin) {
      throw new BadRequestException('priceMax must be >= priceMin');
    }

    const [created] = await this.db
      .insert(products)
      .values({
        umkmId,
        name: dto.name,
        description: dto.description,
        moq: dto.moq,
        monthlyCapacity: dto.monthlyCapacity,
        priceMin: dto.priceMin.toString(),
        priceMax: dto.priceMax.toString(),
        hpp: dto.hpp.toString(),
        photoUrls: dto.photoUrls ?? [],
      })
      .returning();
    if (!created) throw new Error('Failed to create product');

    // Dispatch embedding job (non-blocking)
    await this.verificationProducer.dispatchEmbeddingGeneration({
      productId: created.id,
      description: `${created.name}. ${created.description}`,
      umkmId,
    });

    // Strip HPP before returning
    const { hpp: _hpp, ...safe } = created;
    return safe as Product;
  }

  async listByUmkm(umkmId: string): Promise<Product[]> {
    const rows = await this.db.select().from(products).where(eq(products.umkmId, umkmId));
    // biome-ignore lint/correctness/noUnusedVariables: stripping HPP
    return rows.map(({ hpp, ...r }) => r as Product);
  }

  async update(
    umkmId: string,
    productId: string,
    dto: {
      name?: string; description?: string; moq?: number; monthlyCapacity?: number;
      priceMin?: number; priceMax?: number; photoUrls?: string[];
    },
    userId: string,
  ): Promise<Product> {
    const umkm = await this.umkmService.findById(umkmId);
    if (umkm.userId !== userId) throw new ForbiddenException('Not your UMKM');

    const existing = await this.db.query.products.findFirst({ where: eq(products.id, productId) });
    if (!existing || existing.umkmId !== umkmId) {
      throw new NotFoundException(`Product ${productId} not found`);
    }

    const nextMin = dto.priceMin ?? Number(existing.priceMin);
    const nextMax = dto.priceMax ?? Number(existing.priceMax);
    if (nextMax < nextMin) throw new BadRequestException('priceMax must be >= priceMin');

    const [updated] = await this.db
      .update(products)
      .set({
        ...(dto.name !== undefined ? { name: dto.name } : {}),
        ...(dto.description !== undefined ? { description: dto.description } : {}),
        ...(dto.moq !== undefined ? { moq: dto.moq } : {}),
        ...(dto.monthlyCapacity !== undefined ? { monthlyCapacity: dto.monthlyCapacity } : {}),
        ...(dto.priceMin !== undefined ? { priceMin: dto.priceMin.toString() } : {}),
        ...(dto.priceMax !== undefined ? { priceMax: dto.priceMax.toString() } : {}),
        ...(dto.photoUrls !== undefined ? { photoUrls: dto.photoUrls } : {}),
        updatedAt: new Date(),
      })
      .where(eq(products.id, productId))
      .returning();
    if (!updated) throw new NotFoundException(`Product ${productId} not found`);

    const { hpp: _hpp, ...safe } = updated;
    return safe as Product;
  }
}