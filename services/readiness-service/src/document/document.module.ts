import { Module } from '@nestjs/common';
import { DocumentChecklistController } from './document-checklist.controller.js';
import { DocumentChecklistService } from './document-checklist.service.js';

@Module({
  controllers: [DocumentChecklistController],
  providers: [DocumentChecklistService],
})
export class DocumentModule {}