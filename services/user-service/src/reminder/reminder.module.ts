import { Module } from '@nestjs/common';
import { ReminderController } from './reminder.controller.js';
import { ReminderService } from './reminder.service.js';

@Module({
  controllers: [ReminderController],
  providers: [ReminderService],
})
export class ReminderModule {}
