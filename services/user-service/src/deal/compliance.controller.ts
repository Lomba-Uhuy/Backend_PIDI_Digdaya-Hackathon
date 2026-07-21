import { Controller, Get, Param, ParseUUIDPipe, Post } from '@nestjs/common';
import { ApiBearerAuth, ApiOperation, ApiTags } from '@nestjs/swagger';
import { CurrentUser, type InternalUser } from '../common/current-user.decorator.js';
import { ComplianceService } from './compliance.service.js';

@ApiTags('Compliance')
@ApiBearerAuth()
@Controller('deals/:dealId/compliance')
export class ComplianceController {
  constructor(private readonly complianceService: ComplianceService) {}

  @Get()
  @ApiOperation({ summary: 'List compliance checks for a deal' })
  list(@Param('dealId', ParseUUIDPipe) dealId: string, @CurrentUser() user: InternalUser) {
    return this.complianceService.list(dealId, user.userId);
  }

  @Post('run')
  @ApiOperation({ summary: 'Run/refresh compliance checks from real deal + product data' })
  run(@Param('dealId', ParseUUIDPipe) dealId: string, @CurrentUser() user: InternalUser) {
    return this.complianceService.run(dealId, user.userId);
  }
}
