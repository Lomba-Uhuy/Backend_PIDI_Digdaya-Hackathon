import { Body, Controller, Get, HttpCode, Param, Post, ParseUUIDPipe } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { CurrentUser, type InternalUser } from '../common/current-user.decorator.js';
import { CreateProductDto } from './dto/create-product.dto.js';
import { ProductService } from './product.service.js';

@ApiTags('Products')
@Controller('umkm/:umkmId/products')
export class ProductController {
  constructor(private readonly productService: ProductService) {}

  @Post()
  @HttpCode(201)
  create(
    @Param('umkmId', ParseUUIDPipe) umkmId: string,
    @Body() dto: CreateProductDto,
    @CurrentUser() user: InternalUser,
  ) {
    return this.productService.create(umkmId, dto, user.userId);
  }

  @Get()
  list(@Param('umkmId', ParseUUIDPipe) umkmId: string) {
    return this.productService.listByUmkm(umkmId);
  }
}