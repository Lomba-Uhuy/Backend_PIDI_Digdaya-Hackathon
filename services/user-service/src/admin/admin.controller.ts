import { Body, Controller, Get, Param, Patch, Post, Query, UseGuards } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { CurrentUser, type InternalUser } from '../common/current-user.decorator.js';
import { Roles } from '../authz/authz.decorators.js';
import { RolesGuard } from '../authz/roles.guard.js';
import { AdminService } from './admin.service.js';
import { AuditService, type AuditActor } from './audit.service.js';

const toInt = (v: string | undefined, d: number): number => {
  const n = parseInt(v ?? '', 10);
  return Number.isFinite(n) ? n : d;
};

/**
 * Administration API. EVERY route requires the `admin` role (RolesGuard reads the
 * gateway-injected x-user-role). Admins are cross-tenant and are never subject to
 * subscription feature gating. Mutations are audited.
 */
@ApiTags('Admin')
@UseGuards(RolesGuard)
@Roles('admin')
@Controller('admin')
export class AdminController {
  constructor(
    private readonly admin: AdminService,
    private readonly audit: AuditService,
  ) {}

  private actor(u: InternalUser): AuditActor {
    return { userId: u.userId, email: u.email, ip: u.ip };
  }

  @Get('metrics')
  @ApiOperation({ summary: 'Dashboard metrics (real aggregates)' })
  metrics() {
    return this.admin.metrics();
  }

  @Get('users')
  users(
    @Query('search') search?: string,
    @Query('page') page?: string,
    @Query('limit') limit?: string,
    @Query('role') role?: string,
    @Query('status') status?: string,
  ) {
    return this.admin.listUsers({ search, page: toInt(page, 1), limit: toInt(limit, 20), role, status });
  }

  @Get('users/:id')
  user(@Param('id') id: string) {
    return this.admin.getUser(id);
  }

  @Patch('users/:id/role')
  setRole(@Param('id') id: string, @Body() body: { role: string }, @CurrentUser() u: InternalUser) {
    return this.admin.setUserRole(id, body.role, this.actor(u));
  }

  @Patch('users/:id/plan')
  setPlan(@Param('id') id: string, @Body() body: { plan: string }, @CurrentUser() u: InternalUser) {
    return this.admin.setUserPlan(id, body.plan, this.actor(u));
  }

  @Get('companies')
  companies(@Query('page') page?: string, @Query('limit') limit?: string) {
    return this.admin.listCompanies({ page: toInt(page, 1), limit: toInt(limit, 20) });
  }

  @Get('products')
  products(@Query('page') page?: string, @Query('limit') limit?: string) {
    return this.admin.listProducts({ page: toInt(page, 1), limit: toInt(limit, 20) });
  }

  @Get('workflows')
  workflows(@Query('status') status?: string, @Query('page') page?: string, @Query('limit') limit?: string) {
    return this.admin.listWorkflows({ status, page: toInt(page, 1), limit: toInt(limit, 20) });
  }

  @Post('workflows/:productId/retry')
  retry(@Param('productId') productId: string, @CurrentUser() u: InternalUser) {
    return this.admin.retryWorkflow(productId, this.actor(u));
  }

  @Get('subscriptions')
  subscriptions() {
    return this.admin.listSubscriptions();
  }

  @Get('providers')
  providers() {
    return this.admin.providers();
  }

  @Get('activity')
  activity(@Query('limit') limit?: string) {
    return this.admin.activity(toInt(limit, 40));
  }

  @Get('audit')
  auditLog(@Query('action') action?: string, @Query('limit') limit?: string, @Query('offset') offset?: string) {
    return this.audit.list({ action, limit: toInt(limit, 50), offset: toInt(offset, 0) });
  }
}
