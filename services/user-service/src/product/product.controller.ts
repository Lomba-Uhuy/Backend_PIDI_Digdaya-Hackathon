import {
  Body,
  Controller,
  Get,
  HttpCode,
  Param,
  Patch,
  Post,
  ParseUUIDPipe,
  UseGuards,
} from "@nestjs/common";
import {
  ApiBearerAuth,
  ApiBody,
  ApiCreatedResponse,
  ApiOkResponse,
  ApiParam,
  ApiTags,
} from "@nestjs/swagger";
import {
  CurrentUser,
  type InternalUser,
} from "../common/current-user.decorator.js";
import { Roles } from "../authz/authz.decorators.js";
import { RolesGuard } from "../authz/roles.guard.js";
import { CreateProductDto } from "./dto/create-product.dto.js";
import { UpdateProductDto } from "./dto/update-product.dto.js";
import { ProductService } from "./product.service.js";

const createProductExample = {
  name: "Kopi Arabika Gayo Grade A",
  description:
    "Kopi arabika specialty dari Aceh Tengah, proses semi-washed, cocok untuk pasar roastery premium.",
  moq: 50,
  monthlyCapacity: 10000,
  priceMin: 5.5,
  priceMax: 6.5,
  hpp: 3.5,
  photoUrls: [
    "https://storage.tradeconnect.id/products/gayo-grade-a-1.jpg",
    "https://storage.tradeconnect.id/products/gayo-grade-a-2.jpg",
  ],
};

const productResponseExample = {
  id: "5d9f2d9e-0f0f-4cb0-9d84-1d7a9ef5d8d7",
  umkmId: "c4a4d75b-4d84-4b31-9a7d-8ad6c1a7f1c4",
  name: "Kopi Arabika Gayo Grade A",
  description:
    "Kopi arabika specialty dari Aceh Tengah, proses semi-washed, cocok untuk pasar roastery premium.",
  hsCode: "090121",
  hsConfidence: "0.9400",
  moq: 50,
  monthlyCapacity: 10000,
  priceMin: "5.5000",
  priceMax: "6.5000",
  photoUrls: [
    "https://storage.tradeconnect.id/products/gayo-grade-a-1.jpg",
    "https://storage.tradeconnect.id/products/gayo-grade-a-2.jpg",
  ],
  createdAt: "2026-05-23T03:54:00.000Z",
  updatedAt: "2026-05-23T03:54:00.000Z",
};

@ApiTags("Products")
@ApiBearerAuth()
@Controller("umkm/:umkmId/products")
export class ProductController {
  constructor(private readonly productService: ProductService) {}

  @Post()
  @HttpCode(201)
  @UseGuards(RolesGuard)
  @Roles("umkm") // Product creation belongs to UMKM only; admins are rejected (403).
  @ApiParam({
    name: "umkmId",
    format: "uuid",
    example: "c4a4d75b-4d84-4b31-9a7d-8ad6c1a7f1c4",
  })
  @ApiBody({
    type: CreateProductDto,
    examples: { default: { value: createProductExample } },
  })
  @ApiCreatedResponse({ schema: { example: productResponseExample } })
  create(
    @Param("umkmId", ParseUUIDPipe) umkmId: string,
    @Body() dto: CreateProductDto,
    @CurrentUser() user: InternalUser,
  ) {
    return this.productService.create(umkmId, dto, user.userId);
  }

  @Get()
  @ApiParam({
    name: "umkmId",
    format: "uuid",
    example: "c4a4d75b-4d84-4b31-9a7d-8ad6c1a7f1c4",
  })
  @ApiOkResponse({ schema: { example: [productResponseExample] } })
  list(@Param("umkmId", ParseUUIDPipe) umkmId: string) {
    return this.productService.listByUmkm(umkmId);
  }

  @Patch(":productId")
  @ApiParam({ name: "umkmId", format: "uuid" })
  @ApiParam({ name: "productId", format: "uuid" })
  @ApiOkResponse({ schema: { example: productResponseExample } })
  update(
    @Param("umkmId", ParseUUIDPipe) umkmId: string,
    @Param("productId", ParseUUIDPipe) productId: string,
    @Body() dto: UpdateProductDto,
    @CurrentUser() user: InternalUser,
  ) {
    return this.productService.update(umkmId, productId, dto, user.userId);
  }

  @Patch(":productId/classification")
  @ApiParam({ name: "umkmId", format: "uuid" })
  @ApiParam({ name: "productId", format: "uuid" })
  @ApiOkResponse({ description: "Persist the RAG HS classification (primary + candidates)." })
  saveClassification(
    @Param("umkmId", ParseUUIDPipe) umkmId: string,
    @Param("productId", ParseUUIDPipe) productId: string,
    @Body()
    body: {
      hsCode?: string;
      hsConfidence?: number;
      candidates?: Array<{ hs_code: string; description?: string; confidence?: number; category?: string }>;
      modelVersion?: string;
    },
    @CurrentUser() user: InternalUser,
  ) {
    return this.productService.saveClassification(umkmId, productId, user.userId, {
      hsCode: body.hsCode,
      hsConfidence: body.hsConfidence,
      candidates: body.candidates ?? [],
      modelVersion: body.modelVersion,
    });
  }
}
