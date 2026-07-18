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

export class PricingDto {
  @ApiProperty({ example: 3.5, minimum: 0.01 })
  @IsNumber()
  @Min(0.01)
  hpp!: number;

  @ApiProperty({ example: 0.5, minimum: 0 })
  @IsNumber()
  @Min(0)
  originCharges!: number;

  @ApiProperty({ example: 500, minimum: 1 })
  @IsInt()
  @Min(1)
  qty!: number;

  @ApiProperty({ example: 0.3, minimum: 0 })
  @IsNumber()
  @Min(0)
  oceanFreight!: number;

  @ApiPropertyOptional({ example: 4.4, minimum: 0 })
  @IsNumber()
  @Min(0)
  @IsOptional()
  insuranceAmount?: number;

  @ApiPropertyOptional({ example: 0.002, minimum: 0, maximum: 1 })
  @IsNumber()
  @Min(0)
  @Max(1)
  @IsOptional()
  insuranceRate?: number;

  @ApiPropertyOptional({ example: 0.1, minimum: 0 })
  @IsNumber()
  @Min(0)
  @IsOptional()
  exportDuty?: number;

  @ApiPropertyOptional({ example: 20, minimum: 0, maximum: 200 })
  @IsNumber()
  @Min(0)
  @Max(200)
  @IsOptional()
  profitMarginPct?: number;

  @ApiPropertyOptional({
    example: "0901",
    description: "HS code for BPS benchmark comparison",
  })
  @IsString()
  @MinLength(2)
  @MaxLength(10)
  @IsOptional()
  hsCode?: string;

  @ApiPropertyOptional({
    example: 16000,
    minimum: 1,
    description: "Exchange rate IDR per 1 USD",
  })
  @IsNumber()
  @Min(1)
  @IsOptional()
  exchangeRate?: number;
}
