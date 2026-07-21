import {
  Body, Controller, Delete, Get, HttpCode, Param, ParseUUIDPipe, Post,
} from '@nestjs/common';
import { ApiBearerAuth, ApiOperation, ApiTags } from '@nestjs/swagger';
import { CurrentUser, type InternalUser } from '../common/current-user.decorator.js';
import { CreateReminderDto } from './dto/create-reminder.dto.js';
import { ReminderService } from './reminder.service.js';

@ApiTags('Reminders')
@ApiBearerAuth()
@Controller('reminders')
export class ReminderController {
  constructor(private readonly reminderService: ReminderService) {}

  @Get()
  @ApiOperation({ summary: 'List reminders for the caller' })
  list(@CurrentUser() user: InternalUser) {
    return this.reminderService.list(user.userId);
  }

  @Post()
  @HttpCode(201)
  @ApiOperation({ summary: 'Create a reminder' })
  create(@Body() dto: CreateReminderDto, @CurrentUser() user: InternalUser) {
    return this.reminderService.create(dto, user.userId);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Delete a reminder' })
  remove(@Param('id', ParseUUIDPipe) id: string, @CurrentUser() user: InternalUser) {
    return this.reminderService.remove(id, user.userId);
  }
}
