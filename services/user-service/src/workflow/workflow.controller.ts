import { Controller, Get, HttpCode, Param, ParseUUIDPipe, Post } from '@nestjs/common';
import { ApiBearerAuth, ApiOperation, ApiTags } from '@nestjs/swagger';
import { CurrentUser, type InternalUser } from '../common/current-user.decorator.js';
import { WorkflowService } from './workflow.service.js';

@ApiTags('Product Workflow')
@ApiBearerAuth()
@Controller('products/:productId/workflow')
export class WorkflowController {
  constructor(private readonly workflow: WorkflowService) {}

  @Get()
  @ApiOperation({ summary: 'Product initialization workflow (status + stages + progress)' })
  get(@Param('productId', ParseUUIDPipe) productId: string, @CurrentUser() user: InternalUser) {
    return this.workflow.getWorkflow(productId, user.userId);
  }

  @Get('stages')
  @ApiOperation({ summary: 'Workflow stages (each independently observable)' })
  stages(@Param('productId', ParseUUIDPipe) productId: string, @CurrentUser() user: InternalUser) {
    return this.workflow.getStages(productId, user.userId);
  }

  @Get('events')
  @ApiOperation({ summary: 'Workflow event log (persisted lifecycle events)' })
  events(@Param('productId', ParseUUIDPipe) productId: string, @CurrentUser() user: InternalUser) {
    return this.workflow.getEvents(productId, user.userId);
  }

  @Post()
  @HttpCode(202)
  @ApiOperation({ summary: 'Start (or retry a failed) initialization workflow — idempotent' })
  start(@Param('productId', ParseUUIDPipe) productId: string, @CurrentUser() user: InternalUser) {
    return this.workflow.startForProductByUser(productId, user.userId);
  }
}
