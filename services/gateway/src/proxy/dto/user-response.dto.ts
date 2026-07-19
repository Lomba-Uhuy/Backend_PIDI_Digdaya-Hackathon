import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";

export class UmkmResponseDto {
  @ApiProperty({ format: "uuid" })
  id!: string;

  @ApiProperty({ example: "CV Kopi Gayo Nusantara" })
  legalName!: string;

  @ApiProperty({ example: "1234567890123", description: "NIB — Nomor Induk Berusaha (13 digits)" })
  nib!: string;

  @ApiPropertyOptional({ example: "Produsen kopi arabika specialty dari Takengon, Aceh Tengah." })
  description?: string;

  @ApiProperty({ example: "PENDING", enum: ["PENDING", "VERIFIED", "REJECTED"] })
  verificationStatus!: string;

  @ApiProperty({ example: "0.0000", description: "Composite readiness score [0-1]" })
  verifiedScore!: string;

  @ApiProperty({ example: { nibValid: true, businessName: "CV Kopi Gayo Nusantara" } })
  ossRbaData!: Record<string, unknown>;

  @ApiProperty({ example: {} })
  inatradeData!: Record<string, unknown>;

  @ApiProperty({ type: [String], example: ["halal", "organic"] })
  certifications!: string[];

  @ApiProperty({ format: "uuid" })
  userId!: string;

  @ApiProperty({ example: true })
  isActive!: boolean;

  @ApiProperty({ format: "date-time" })
  createdAt!: string;

  @ApiProperty({ format: "date-time" })
  updatedAt!: string;
}

export class ProductResponseDto {
  @ApiProperty({ format: "uuid" })
  id!: string;

  @ApiProperty({ format: "uuid" })
  umkmId!: string;

  @ApiProperty({ example: "Kopi Arabika Gayo Grade A" })
  name!: string;

  @ApiProperty({ example: "Kopi arabika specialty dari Aceh Tengah, proses semi-washed." })
  description!: string;

  @ApiProperty({ example: "090121", description: "HS code auto-classified by AI" })
  hsCode!: string;

  @ApiProperty({ example: "0.9400", description: "AI confidence for the HS code [0-1]" })
  hsConfidence!: string;

  @ApiProperty({ example: 50, description: "Minimum Order Quantity (units)" })
  moq!: number;

  @ApiProperty({ example: 10000, description: "Monthly production capacity (units)" })
  monthlyCapacity!: number;

  @ApiProperty({ example: "5.5000", description: "Minimum listing price (USD)" })
  priceMin!: string;

  @ApiProperty({ example: "6.5000", description: "Maximum / target price (USD)" })
  priceMax!: string;

  @ApiProperty({ type: [String], example: ["https://storage.tradeconnect.id/products/img.jpg"] })
  photoUrls!: string[];

  @ApiProperty({ format: "date-time" })
  createdAt!: string;

  @ApiProperty({ format: "date-time" })
  updatedAt!: string;
}
