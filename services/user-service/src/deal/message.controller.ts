import {
  Body, Controller, Get, HttpCode, Param, ParseUUIDPipe, Post,
} from '@nestjs/common';
import { ApiBearerAuth, ApiOperation, ApiTags } from '@nestjs/swagger';
import { CurrentUser, type InternalUser } from '../common/current-user.decorator.js';
import { CreateMessageDto } from './dto/create-message.dto.js';
import { MessageService } from './message.service.js';

@ApiTags('Deal Messages')
@ApiBearerAuth()
@Controller('deals/:dealId/messages')
export class MessageController {
  constructor(private readonly messageService: MessageService) {}

  @Get()
  @ApiOperation({ summary: 'List messages for a deal (oldest first)' })
  list(
    @Param('dealId', ParseUUIDPipe) dealId: string,
    @CurrentUser() user: InternalUser,
  ) {
    return this.messageService.list(dealId, user.userId);
  }

  @Post()
  @HttpCode(201)
  @ApiOperation({ summary: 'Append a message to a deal' })
  create(
    @Param('dealId', ParseUUIDPipe) dealId: string,
    @Body() dto: CreateMessageDto,
    @CurrentUser() user: InternalUser,
  ) {
    return this.messageService.create(
      dealId,
      { text: dto.text, sender: dto.sender, intent: dto.intent },
      user.userId,
    );
  }
}
