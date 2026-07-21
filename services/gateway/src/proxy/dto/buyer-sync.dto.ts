import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import {
  ArrayMinSize,
  IsArray,
  IsInt,
  IsOptional,
  IsString,
  Max,
  Min,
} from "class-validator";

export class BuyerSyncDto {
  @ApiProperty({ type: [String], example: ["090111"], description: "HS codes from the product RAG/classifier" })
  @IsArray()
  @ArrayMinSize(1)
  @IsString({ each: true })
  hs_codes!: string[];

  @ApiPropertyOptional({ type: [String], example: ["United States"], description: "User-selected target markets" })
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  importer_countries?: string[];

  @ApiPropertyOptional({ type: [String] })
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  exporter_countries?: string[];

  @ApiPropertyOptional({ example: "2022-01-01" })
  @IsOptional()
  @IsString()
  start_date?: string;

  @ApiPropertyOptional({ example: "2022-12-31" })
  @IsOptional()
  @IsString()
  end_date?: string;

  @ApiPropertyOptional({ example: 40, minimum: 1, maximum: 1000 })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(1000)
  max_pages?: number;
}
