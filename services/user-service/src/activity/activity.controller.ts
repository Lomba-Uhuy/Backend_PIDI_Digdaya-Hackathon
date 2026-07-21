import { Controller, Get, Query } from '@nestjs/common';
import { ApiBearerAuth, ApiOperation, ApiTags } from '@nestjs/swagger';
import { CurrentUser, type InternalUser } from '../common/current-user.decorator.js';
import { ActivityService } from './activity.service.js';

@ApiTags('Activity')
@ApiBearerAuth()
@Controller('activity')
export class ActivityController {
  constructor(private readonly activity: ActivityService) {}

  @Get('recent')
  @ApiOperation({ summary: 'Recent activity feed built from persisted events (deals, PO, sync, product)' })
  recent(
    @CurrentUser() user: InternalUser,
    @Query('limit') limit?: string,
    @Query('offset') offset?: string,
    @Query('category') category?: string,
  ) {
    const l = Math.min(100, Math.max(1, parseInt(limit ?? '15', 10) || 15));
    const o = Math.max(0, parseInt(offset ?? '0', 10) || 0);
    return this.activity.recent(user.userId, { limit: l, offset: o, category });
  }

  @Get('statistics')
  @ApiOperation({ summary: 'Activity counts by category + last synchronization status' })
  statistics(@CurrentUser() user: InternalUser) {
    return this.activity.statistics(user.userId);
  }
}
