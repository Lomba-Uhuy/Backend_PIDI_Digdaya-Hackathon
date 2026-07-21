import { HttpService } from "@nestjs/axios";
import {
  Body,
  Controller,
  Get,
  HttpCode,
  Param,
  Patch,
  Post,
  Req,
  UseGuards,
} from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import {
  ApiBearerAuth,
  ApiBody,
  ApiCreatedResponse,
  ApiOkResponse,
  ApiOperation,
  ApiParam,
  ApiTags,
} from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { JwtAuthGuard } from "../auth/guards/jwt-auth.guard.js";
import { CreateProductDto } from "./dto/create-product.dto.js";
import { CreateUmkmDto } from "./dto/create-umkm.dto.js";
import { UpdateProductDto } from "./dto/update-product.dto.js";
import { UpdateUmkmDto } from "./dto/update-umkm.dto.js";
import { ProductResponseDto, UmkmResponseDto } from "./dto/user-response.dto.js";
import {
  createProductExample,
  createUmkmExample,
} from "./swagger-examples.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("UMKM & Products")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller()
export class UserProxyController {
  private readonly upstream: string;

  constructor(http: HttpService, cfg: ConfigService) {
    this.http = http;
    this.upstream = cfg.getOrThrow<string>("USER_SERVICE_URL");
  }
  private readonly http: HttpService;

  // ── UMKM ──────────────────────────────────────────────────────────────────

  @Post("umkm")
  @HttpCode(201)
  @ApiOperation({ summary: "Create UMKM profile for the authenticated user" })
  @ApiBody({
    type: CreateUmkmDto,
    examples: { default: { value: createUmkmExample } },
  })
  @ApiCreatedResponse({ type: UmkmResponseDto })
  async createUmkm(@Body() body: CreateUmkmDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/umkm`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get("umkm/me")
  @ApiOperation({ summary: "Get UMKM profile of the authenticated user" })
  @ApiOkResponse({ type: UmkmResponseDto })
  async getMyUmkm(@Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/umkm/me`, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get("umkm/:umkmId/readiness")
  @ApiOperation({ summary: "Composite export-readiness score for an UMKM" })
  async readiness(@Param("umkmId") umkmId: string, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/umkm/${umkmId}/readiness`, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Patch("umkm/:umkmId")
  @ApiOperation({ summary: "Update an UMKM profile (name / description)" })
  @ApiOkResponse({ type: UmkmResponseDto })
  async updateUmkm(
    @Param("umkmId") umkmId: string,
    @Body() body: UpdateUmkmDto,
    @Req() req: any,
  ) {
    try {
      const { data } = await firstValueFrom(
        this.http.patch(`${this.upstream}/umkm/${umkmId}`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  // ── Products ───────────────────────────────────────────────────────────────

  @Post("umkm/:umkmId/products")
  @HttpCode(201)
  @ApiOperation({ summary: "Add a product to an UMKM profile" })
  @ApiParam({ name: "umkmId", format: "uuid", example: "c4a4d75b-4d84-4b31-9a7d-8ad6c1a7f1c4" })
  @ApiBody({
    type: CreateProductDto,
    examples: { default: { value: createProductExample } },
  })
  @ApiCreatedResponse({ type: ProductResponseDto })
  async createProduct(
    @Param("umkmId") umkmId: string,
    @Body() body: CreateProductDto,
    @Req() req: any,
  ) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/umkm/${umkmId}/products`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get("umkm/:umkmId/products")
  @ApiOperation({ summary: "List all products for an UMKM" })
  @ApiParam({ name: "umkmId", format: "uuid", example: "c4a4d75b-4d84-4b31-9a7d-8ad6c1a7f1c4" })
  @ApiOkResponse({ type: [ProductResponseDto] })
  async listProducts(
    @Param("umkmId") umkmId: string,
    @Req() req: any,
  ) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/umkm/${umkmId}/products`, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Patch("umkm/:umkmId/products/:productId")
  @ApiOperation({ summary: "Update a product" })
  @ApiParam({ name: "umkmId", format: "uuid" })
  @ApiParam({ name: "productId", format: "uuid" })
  @ApiOkResponse({ type: ProductResponseDto })
  async updateProduct(
    @Param("umkmId") umkmId: string,
    @Param("productId") productId: string,
    @Body() body: UpdateProductDto,
    @Req() req: any,
  ) {
    try {
      const { data } = await firstValueFrom(
        this.http.patch(`${this.upstream}/umkm/${umkmId}/products/${productId}`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Patch("umkm/:umkmId/products/:productId/classification")
  @ApiOperation({ summary: "Persist the RAG HS classification (primary + top-k candidates)" })
  @ApiParam({ name: "umkmId", format: "uuid" })
  @ApiParam({ name: "productId", format: "uuid" })
  async saveClassification(
    @Param("umkmId") umkmId: string,
    @Param("productId") productId: string,
    @Body() body: unknown,
    @Req() req: any,
  ) {
    try {
      const { data } = await firstValueFrom(
        this.http.patch(`${this.upstream}/umkm/${umkmId}/products/${productId}/classification`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
