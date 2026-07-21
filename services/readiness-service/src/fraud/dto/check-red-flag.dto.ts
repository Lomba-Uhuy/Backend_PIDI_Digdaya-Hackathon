import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import { Type } from "class-transformer";
import {
  IsArray,
  IsBoolean,
  IsDateString,
  IsIn,
  IsOptional,
  IsString,
  MaxLength,
  MinLength,
  ValidateNested,
} from "class-validator";

const BUYER_RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"] as const;
const RED_FLAG_CATEGORIES = [
  "SAMPLE",
  "JURISDICTION",
  "COMMUNICATION",
  "PAYMENT",
] as const;
const COMMUNICATION_SENDERS = ["buyer", "seller", "agent", "other"] as const;

export class BuyerProfileDto {
  @ApiPropertyOptional({ example: "PT Global Trading Asia" })
  @IsOptional()
  @IsString()
  @MaxLength(255)
  companyName?: string;

  @ApiPropertyOptional({
    example: "AE",
    description: "ISO-2 country code or freeform country name",
  })
  @IsOptional()
  @IsString()
  @MaxLength(255)
  country?: string;

  @ApiPropertyOptional({
    example: "AE",
    description: "ISO-2 country code, if known",
  })
  @IsOptional()
  @IsString()
  @MaxLength(8)
  countryCode?: string;

  @ApiPropertyOptional({
    example: true,
    description: "True if buyer asked for sample before contract",
  })
  @IsOptional()
  @IsBoolean()
  requestedSampleBeforeContract?: boolean;

  @ApiPropertyOptional({
    example: false,
    description: "True if buyer asked to pay outside the platform",
  })
  @IsOptional()
  @IsBoolean()
  requestedPaymentOutsidePlatform?: boolean;
}

export class CommunicationHistoryEntryDto {
  @ApiPropertyOptional({ example: "buyer", enum: COMMUNICATION_SENDERS })
  @IsOptional()
  @IsIn(COMMUNICATION_SENDERS)
  sender?: (typeof COMMUNICATION_SENDERS)[number];

  @ApiProperty({
    example: "Please send sample first before we finalize the contract.",
  })
  @IsString()
  @MinLength(1)
  @MaxLength(4000)
  message!: string;

  @ApiPropertyOptional({ example: "2026-05-29T10:00:00Z" })
  @IsOptional()
  @IsDateString()
  sentAt?: string;

  @ApiPropertyOptional({ example: "email" })
  @IsOptional()
  @IsString()
  @MaxLength(64)
  channel?: string;
}

export class CheckRedFlagDto {
  @ApiProperty({ type: BuyerProfileDto })
  @ValidateNested()
  @Type(() => BuyerProfileDto)
  buyerProfile!: BuyerProfileDto;

  @ApiProperty({ type: [CommunicationHistoryEntryDto] })
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => CommunicationHistoryEntryDto)
  communicationHistory!: CommunicationHistoryEntryDto[];
}

export class RedFlagFindingDto {
  @ApiProperty({ example: "sample_before_contract" })
  @IsString()
  id!: string;

  @ApiProperty({
    example: "Buyer meminta sampel sebelum kontrak atau PO",
    maxLength: 255,
  })
  @IsString()
  description!: string;

  @ApiProperty({ example: "SAMPLE", enum: RED_FLAG_CATEGORIES })
  @IsIn(RED_FLAG_CATEGORIES)
  category!: (typeof RED_FLAG_CATEGORIES)[number];

  @ApiProperty({ example: "MEDIUM", enum: BUYER_RISK_LEVELS })
  @IsIn(BUYER_RISK_LEVELS)
  severity!: (typeof BUYER_RISK_LEVELS)[number];

  @ApiProperty({
    example:
      "message=Please send sample first before we finalize the contract.",
  })
  @IsString()
  evidence!: string;
}

export class CheckRedFlagResponseDto {
  @ApiProperty({ example: "HIGH", enum: BUYER_RISK_LEVELS })
  @IsIn(BUYER_RISK_LEVELS)
  riskLevel!: (typeof BUYER_RISK_LEVELS)[number];

  @ApiProperty({ type: [RedFlagFindingDto] })
  @IsArray()
  flags!: RedFlagFindingDto[];

  @ApiProperty({
    example:
      "Tunda transaksi, verifikasi identitas buyer, dan minta pembayaran melalui platform resmi.",
  })
  @IsString()
  recommendation!: string;
}
