import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import {
  IsInt,
  IsNumber,
  IsOptional,
  IsString,
  Max,
  MaxLength,
  Min,
  MinLength,
} from "class-validator";

export class PricingInputDto {
  @ApiProperty({
    example: 3.5,
    minimum: 0.01,
    description: "Harga Pokok Produksi (HPP) per unit dalam USD",
  })
  @IsNumber()
  @Min(0.01)
  hpp!: number;

  @ApiProperty({
    example: 0.5,
    minimum: 0,
    description: "Ongkos kirim domestik ke pelabuhan per unit (USD)",
  })
  @IsNumber()
  @Min(0)
  originCharges!: number;

  @ApiProperty({ example: 500, minimum: 1, description: "Jumlah unit" })
  @IsInt()
  @Min(1)
  qty!: number;

  @ApiProperty({
    example: 0.3,
    minimum: 0,
    description: "Freight internasional total (USD)",
  })
  @IsNumber()
  @Min(0)
  oceanFreight!: number;

  @ApiPropertyOptional({
    example: 4.4,
    minimum: 0,
    description: "Biaya asuransi internasional total (USD)",
  })
  @IsNumber()
  @Min(0)
  @IsOptional()
  insuranceAmount?: number;

  @ApiPropertyOptional({
    example: 0.002,
    minimum: 0,
    maximum: 1,
    description:
      "Legacy insurance rate (decimal); used if insuranceAmount is not provided",
  })
  @IsNumber()
  @Min(0)
  @Max(1)
  @IsOptional()
  insuranceRate?: number;

  @ApiPropertyOptional({
    example: 0.1,
    minimum: 0,
    description: "Bea ekspor / export duty total (USD)",
  })
  @IsNumber()
  @Min(0)
  @IsOptional()
  exportDuty?: number;

  @ApiPropertyOptional({
    example: 20,
    minimum: 0,
    maximum: 200,
    description: "Profit margin percentage (default 20%)",
  })
  @IsNumber()
  @Min(0)
  @Max(200)
  @IsOptional()
  profitMarginPct?: number;

  @ApiPropertyOptional({
    example: "0901",
    description: "HS code for BPS benchmark comparison (2-6 digit)",
  })
  @IsString()
  @MinLength(2)
  @MaxLength(10)
  @IsOptional()
  hsCode?: string;

  @ApiPropertyOptional({
    example: 16000,
    minimum: 1,
    description: "Exchange rate IDR per 1 USD (default 16000)",
  })
  @IsNumber()
  @Min(1)
  @IsOptional()
  exchangeRate?: number;
}
