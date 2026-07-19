import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import { IsNumber, IsOptional, IsString, Min } from "class-validator";

export class GenerateDocsDto {
  @ApiProperty({
    example: "prod-1234-uuid",
    description: "Product ID to look up product details",
  })
  @IsString()
  productId!: string;

  @ApiProperty({
    example: "umkm-5678-uuid",
    description: "UMKM ID to look up owner profile",
  })
  @IsString()
  umkmId!: string;

  @ApiProperty({
    example: 2.75,
    description: "Agreed unit price per kg in USD",
  })
  @IsNumber()
  @Min(0.01)
  agreedPrice!: number;

  @ApiPropertyOptional({
    example: 18.0,
    description: "Quantity of export product in Metric Tons",
  })
  @IsNumber()
  @Min(0.1)
  @IsOptional()
  quantity?: number;

  @ApiPropertyOptional({ example: "GlobalTech Imports GmbH", description: "Buyer/consignee company name" })
  @IsString()
  @IsOptional()
  buyerName?: string;

  @ApiPropertyOptional({ example: "Frankfurt, Germany", description: "Buyer/consignee city and country" })
  @IsString()
  @IsOptional()
  buyerLocation?: string;

  @ApiPropertyOptional({ example: "DE", description: "ISO-2 buyer country code" })
  @IsString()
  @IsOptional()
  buyerCountry?: string;
}
