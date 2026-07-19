import {
  Body,
  Controller,
  Get,
  HttpCode,
  NotFoundException,
  Param,
  ParseUUIDPipe,
  Patch,
  Post,
} from "@nestjs/common";
import {
  ApiBearerAuth,
  ApiBody,
  ApiCreatedResponse,
  ApiOkResponse,
  ApiTags,
} from "@nestjs/swagger";
import {
  CurrentUser,
  type InternalUser,
} from "../common/current-user.decorator.js";
import { CreateUmkmDto } from "./dto/create-umkm.dto.js";
import { UpdateUmkmDto } from "./dto/update-umkm.dto.js";
import { UmkmService } from "./umkm.service.js";

const createUmkmExample = {
  legalName: "CV Kopi Gayo Nusantara",
  nib: "1234567890123",
  description: "Produsen kopi arabika specialty dari Takengon, Aceh Tengah.",
};

const umkmResponseExample = {
  id: "c4a4d75b-4d84-4b31-9a7d-8ad6c1a7f1c4",
  legalName: "CV Kopi Gayo Nusantara",
  nib: "1234567890123",
  description: "Produsen kopi arabika specialty dari Takengon, Aceh Tengah.",
  verificationStatus: "PENDING",
  verifiedScore: "0.0000",
  ossRbaData: {
    nibValid: true,
    businessName: "CV Kopi Gayo Nusantara",
  },
  inatradeData: {},
  certifications: ["halal", "organic"],
  userId: "550e8400-e29b-41d4-a716-446655440000",
  isActive: true,
  createdAt: "2026-05-23T03:54:00.000Z",
  updatedAt: "2026-05-23T03:54:00.000Z",
};

@ApiTags("UMKM")
@ApiBearerAuth()
@Controller("umkm")
export class UmkmController {
  constructor(private readonly umkmService: UmkmService) {}

  @Post()
  @HttpCode(201)
  @ApiBody({
    type: CreateUmkmDto,
    examples: { default: { value: createUmkmExample } },
  })
  @ApiCreatedResponse({ schema: { example: umkmResponseExample } })
  create(@Body() dto: CreateUmkmDto, @CurrentUser() user: InternalUser) {
    return this.umkmService.create(dto, user.userId);
  }

  @Get("me")
  @ApiOkResponse({ schema: { example: umkmResponseExample } })
  async me(@CurrentUser() user: InternalUser) {
    const umkm = await this.umkmService.findByUser(user.userId);
    if (!umkm) throw new NotFoundException("No UMKM profile for this user yet");
    return umkm;
  }

  @Get(":umkmId/readiness")
  @ApiOkResponse({ schema: { example: { umkmId: "c4a4d75b-4d84-4b31-9a7d-8ad6c1a7f1c4", score: 85, level: "ready", breakdown: [] } } })
  readiness(@Param("umkmId", ParseUUIDPipe) umkmId: string, @CurrentUser() user: InternalUser) {
    return this.umkmService.readiness(umkmId, user.userId);
  }

  @Patch(":id")
  @ApiOkResponse({ schema: { example: umkmResponseExample } })
  update(
    @Param("id", ParseUUIDPipe) id: string,
    @Body() dto: UpdateUmkmDto,
    @CurrentUser() user: InternalUser,
  ) {
    return this.umkmService.update(id, dto, user.userId);
  }
}
