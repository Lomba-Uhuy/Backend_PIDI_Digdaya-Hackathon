import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsArray, IsInt, IsOptional, IsString, Min } from 'class-validator';

export class MatchingSearchDto {
  @ApiProperty({ example: '5d9f2d9e-0f0f-4cb0-9d84-1d7a9ef5d8d7' })
  @IsString()
  product_id!: string;

  @ApiPropertyOptional({ example: 5, minimum: 1, maximum: 50 })
  @IsInt()
  @Min(1)
  @IsOptional()
  top_k?: number;

  @ApiPropertyOptional({ example: ['DE', 'NL', 'JP'], type: [String] })
  @IsArray()
  @IsString({ each: true })
  @IsOptional()
  country_filter?: string[];
}
