import { ForbiddenException, Inject, Injectable, NotFoundException } from '@nestjs/common';
import { and, asc, eq } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import { reminders, type Reminder } from '../database/schema/index.js';
import type { CreateReminderDto } from './dto/create-reminder.dto.js';

@Injectable()
export class ReminderService {
  constructor(@Inject(DRIZZLE) private readonly db: DrizzleDB) {}

  async create(dto: CreateReminderDto, userId: string): Promise<Reminder> {
    const [created] = await this.db
      .insert(reminders)
      .values({
        userId,
        title: dto.title,
        remindAt: new Date(dto.remindAt),
        type: dto.type ?? 'general',
      })
      .returning();
    if (!created) throw new Error('Failed to create reminder');
    return created;
  }

  async list(userId: string): Promise<Reminder[]> {
    return this.db
      .select()
      .from(reminders)
      .where(eq(reminders.userId, userId))
      .orderBy(asc(reminders.remindAt));
  }

  async remove(id: string, userId: string): Promise<{ deleted: boolean }> {
    const row = await this.db.query.reminders.findFirst({ where: eq(reminders.id, id) });
    if (!row) throw new NotFoundException(`Reminder ${id} not found`);
    if (row.userId !== userId) throw new ForbiddenException('Not your reminder');
    await this.db.delete(reminders).where(and(eq(reminders.id, id), eq(reminders.userId, userId)));
    return { deleted: true };
  }
}
