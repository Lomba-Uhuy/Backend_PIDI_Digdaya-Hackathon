import { ApiPropertyOptional } from '@nestjs/swagger';
import {
  IsArray, IsInt, IsNumber, IsOptional, IsString, IsUrl, Length, Min,
} from 'class-validator';

export class UpdateProductDto {
  @ApiPropertyOptional({ example: 'Kopi Arabika Gayo Grade A', maxLength: 255 })
  @IsOptional()
  @IsString()
  @Length(1, 255)
  name?: string;

  @ApiPropertyOptional({ minLength: 10, maxLength: 5000 })
  @IsOptional()
  @IsString()
  @Length(10, 5000)
  description?: string;

  @ApiPropertyOptional({ example: 50, minimum: 1 })
  @IsOptional()
  @IsInt()
  @Min(1)
  moq?: number;

  @ApiPropertyOptional({ example: 10000, minimum: 1 })
  @IsOptional()
  @IsInt()
  @Min(1)
  monthlyCapacity?: number;

  @ApiPropertyOptional({ example: 5.5, minimum: 0 })
  @IsOptional()
  @IsNumber()
  @Min(0)
  priceMin?: number;

  @ApiPropertyOptional({ example: 6.5, minimum: 0 })
  @IsOptional()
  @IsNumber()
  @Min(0)
  priceMax?: number;

  @ApiPropertyOptional({ type: [String] })
  @IsOptional()
  @IsArray()
  @IsUrl({}, { each: true })
  photoUrls?: string[];
}
