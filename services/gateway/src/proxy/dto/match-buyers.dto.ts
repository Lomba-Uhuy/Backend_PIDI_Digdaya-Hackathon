import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import {
  ArrayMaxSize,
  ArrayMinSize,
  IsArray,
  IsInt,
  IsNumber,
  IsOptional,
  IsString,
  Max,
  Min,
} from "class-validator";

export class MatchBuyersDto {
  @ApiProperty({
    description: "Product embedding vector (1024-dim from multilingual-e5-large)",
    type: [Number],
    example: [0.0123, -0.0456, 0.0789],
  })
  @IsArray()
  @ArrayMinSize(1)
  @ArrayMaxSize(4096)
  @IsNumber({}, { each: true })
  embedding!: number[];

  @ApiPropertyOptional({
    description: "Number of buyers to return",
    minimum: 1,
    maximum: 50,
    default: 10,
  })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(50)
  top_k?: number;

  @ApiPropertyOptional({
    description: "Filter by importing country (ISO-2 codes)",
    type: [String],
    example: ["DE", "NL", "JP"],
  })
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  country_filter?: string[];

  @ApiPropertyOptional({
    description: "Minimum buyer MOQ — only return buyers who order at least this volume",
    minimum: 1,
    example: 100,
  })
  @IsOptional()
  @IsNumber()
  @Min(1)
  min_volume?: number;

  @ApiPropertyOptional({
    description: "HS code prefix filter — e.g. '09' for coffee/tea, '0901' for coffee only",
    example: "09",
  })
  @IsOptional()
  @IsString()
  category?: string;
}
