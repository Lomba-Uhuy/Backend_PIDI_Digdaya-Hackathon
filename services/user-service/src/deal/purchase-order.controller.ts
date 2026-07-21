import {
  Body, Controller, Get, Param, ParseUUIDPipe, Post,
} from '@nestjs/common';
import { ApiBearerAuth, ApiOperation, ApiTags } from '@nestjs/swagger';
import { CurrentUser, type InternalUser } from '../common/current-user.decorator.js';
import { SignPoDto } from './dto/sign-po.dto.js';
import { PurchaseOrderService } from './purchase-order.service.js';

@ApiTags('Purchase Orders')
@ApiBearerAuth()
@Controller('deals/:dealId/purchase-order')
export class PurchaseOrderController {
  constructor(private readonly poService: PurchaseOrderService) {}

  @Post()
  @ApiOperation({ summary: 'Generate (once) a PO draft from the deal + product' })
  generate(@Param('dealId', ParseUUIDPipe) dealId: string, @CurrentUser() user: InternalUser) {
    return this.poService.generate(dealId, user.userId);
  }

  @Get()
  @ApiOperation({ summary: 'Get the deal purchase order' })
  get(@Param('dealId', ParseUUIDPipe) dealId: string, @CurrentUser() user: InternalUser) {
    return this.poService.get(dealId, user.userId);
  }

  @Post('send')
  @ApiOperation({ summary: 'Mark PO as sent (advances deal to po_sent)' })
  send(@Param('dealId', ParseUUIDPipe) dealId: string, @CurrentUser() user: InternalUser) {
    return this.poService.send(dealId, user.userId);
  }

  @Post('sign')
  @ApiOperation({ summary: 'Sign the PO (advances deal to po_signed)' })
  sign(
    @Param('dealId', ParseUUIDPipe) dealId: string,
    @Body() dto: SignPoDto,
    @CurrentUser() user: InternalUser,
  ) {
    return this.poService.sign(dealId, { signedBy: dto.signedBy, signature: dto.signature }, user.userId);
  }
}
