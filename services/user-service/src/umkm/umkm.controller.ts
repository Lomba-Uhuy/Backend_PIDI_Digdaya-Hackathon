import { Body, Controller, Get, HttpCode, NotFoundException, Post } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { CurrentUser, type InternalUser } from '../common/current-user.decorator.js';
import { CreateUmkmDto } from './dto/create-umkm.dto.js';
import { UmkmService } from './umkm.service.js';

@ApiTags('UMKM')
@Controller('umkm')
export class UmkmController {
  constructor(private readonly umkmService: UmkmService) {}

  @Post()
  @HttpCode(201)
  create(@Body() dto: CreateUmkmDto, @CurrentUser() user: InternalUser) {
    return this.umkmService.create(dto, user.userId);
  }

  @Get('me')
  async me(@CurrentUser() user: InternalUser) {
    const umkm = await this.umkmService.findByUser(user.userId);
    if (!umkm) throw new NotFoundException('No UMKM profile for this user yet');
    return umkm;
  }
}