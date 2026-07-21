import {
  Body, Controller, Get, HttpCode, Param, ParseUUIDPipe, Patch, Post, Query,
} from '@nestjs/common';
import { ApiBearerAuth, ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { CurrentUser, type InternalUser } from '../common/current-user.decorator.js';
import { CreateDealDto } from './dto/create-deal.dto.js';
import { UpdateDealDto } from './dto/update-deal.dto.js';
import { DealService } from './deal.service.js';

@ApiTags('Deals')
@ApiBearerAuth()
@Controller('deals')
export class DealController {
  constructor(private readonly dealService: DealService) {}

  @Post()
  @HttpCode(201)
  @ApiOperation({ summary: 'Create a deal for the caller UMKM' })
  create(@Body() dto: CreateDealDto, @CurrentUser() user: InternalUser) {
    return this.dealService.create(dto, user.userId);
  }

  @Get()
  @ApiOperation({ summary: 'List deals (paginated) for the caller UMKM' })
  @ApiOkResponse({ description: '{ items, total, page, pageSize }' })
  list(
    @CurrentUser() user: InternalUser,
    @Query('status') status?: string,
    @Query('page') page?: string,
    @Query('pageSize') pageSize?: string,
  ) {
    const p = Math.max(1, parseInt(page ?? '1', 10) || 1);
    const ps = Math.min(100, Math.max(1, parseInt(pageSize ?? '20', 10) || 20));
    return this.dealService.list(user.userId, { status, page: p, pageSize: ps });
  }

  @Get('analytics')
  @ApiOperation({ summary: 'Negotiation analytics (conversion, pipeline, distributions)' })
  analytics(@CurrentUser() user: InternalUser) {
    return this.dealService.analytics(user.userId);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get a single deal' })
  findOne(@Param('id', ParseUUIDPipe) id: string, @CurrentUser() user: InternalUser) {
    return this.dealService.findById(id, user.userId);
  }

  @Patch(':id')
  @ApiOperation({ summary: 'Update a deal (status / agreed price / last message)' })
  update(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() dto: UpdateDealDto,
    @CurrentUser() user: InternalUser,
  ) {
    return this.dealService.update(id, dto, user.userId);
  }
}
