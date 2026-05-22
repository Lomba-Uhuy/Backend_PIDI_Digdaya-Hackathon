import { Controller, Get } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { DocumentChecklistService } from './document-checklist.service.js';

@ApiTags('Document Checklist')
@Controller('documents')
export class DocumentChecklistController {
  constructor(private readonly svc: DocumentChecklistService) {}

  @Get('checklist')
  base() {
    return { items: this.svc.baseChecklist() };
  }
}