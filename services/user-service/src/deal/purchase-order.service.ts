import { BadRequestException, Inject, Injectable, NotFoundException } from '@nestjs/common';
import { eq } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import {
  deals, products, purchaseOrders, type PurchaseOrder,
} from '../database/schema/index.js';
import { DealService } from './deal.service.js';

export interface SignPoInput {
  signedBy: string;
  signature?: string;
}

@Injectable()
export class PurchaseOrderService {
  constructor(
    @Inject(DRIZZLE) private readonly db: DrizzleDB,
    private readonly dealService: DealService,
  ) {}

  /** Generate (once) a PO draft from the deal's agreed price + product. Idempotent. */
  async generate(dealId: string, userId: string): Promise<PurchaseOrder> {
    const deal = await this.dealService.findById(dealId, userId); // ownership

    const existing = await this.db.query.purchaseOrders.findFirst({
      where: eq(purchaseOrders.dealId, dealId),
    });
    if (existing) return existing;

    const unitPrice = deal.agreedPrice != null ? Number(deal.agreedPrice) : null;
    if (unitPrice == null || unitPrice <= 0) {
      throw new BadRequestException(
        'Deal has no agreed price yet — finish the negotiation before issuing a PO',
      );
    }

    let productName: string | null = null;
    let qty = 1;
    if (deal.productId) {
      const product = await this.db.query.products.findFirst({
        where: eq(products.id, deal.productId),
      });
      if (product) {
        productName = product.name;
        qty = product.moq ?? 1;
      }
    }

    const subtotal = unitPrice * qty;
    const poNumber = `PO-${Date.now().toString(36).toUpperCase()}`;

    const [created] = await this.db
      .insert(purchaseOrders)
      .values({
        dealId,
        poNumber,
        productId: deal.productId ?? undefined,
        productName,
        buyerName: deal.buyerName,
        buyerCountry: deal.buyerCountry,
        incoterm: 'CIF',
        unitPrice: String(unitPrice),
        qty,
        currency: 'USD',
        subtotal: String(subtotal),
        paymentTerms: '30% DP / 70% L/C',
        status: 'draft',
      })
      .returning();
    if (!created) throw new Error('Failed to create purchase order');
    return created;
  }

  async get(dealId: string, userId: string): Promise<PurchaseOrder> {
    await this.dealService.findById(dealId, userId); // ownership
    const po = await this.db.query.purchaseOrders.findFirst({
      where: eq(purchaseOrders.dealId, dealId),
    });
    if (!po) throw new NotFoundException('No purchase order for this deal yet');
    return po;
  }

  /** Mark the PO as sent to the buyer and advance the deal to po_sent. */
  async send(dealId: string, userId: string): Promise<PurchaseOrder> {
    await this.get(dealId, userId); // ownership + existence
    const [updated] = await this.db
      .update(purchaseOrders)
      .set({ status: 'sent', updatedAt: new Date() })
      .where(eq(purchaseOrders.dealId, dealId))
      .returning();
    await this.db
      .update(deals)
      .set({ status: 'po_sent', updatedAt: new Date() })
      .where(eq(deals.id, dealId));
    return updated!;
  }

  /** Record the buyer signature and advance the deal to po_signed. */
  async sign(dealId: string, input: SignPoInput, userId: string): Promise<PurchaseOrder> {
    await this.get(dealId, userId); // ownership + existence
    const [updated] = await this.db
      .update(purchaseOrders)
      .set({
        status: 'signed',
        signedBy: input.signedBy,
        signature: input.signature ?? input.signedBy,
        signedAt: new Date(),
        updatedAt: new Date(),
      })
      .where(eq(purchaseOrders.dealId, dealId))
      .returning();
    await this.db
      .update(deals)
      .set({ status: 'po_signed', updatedAt: new Date() })
      .where(eq(deals.id, dealId));
    return updated!;
  }
}
