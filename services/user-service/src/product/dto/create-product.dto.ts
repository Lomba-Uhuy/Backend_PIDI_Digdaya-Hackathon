import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import {
  IsArray,
  IsInt,
  IsNumber,
  IsOptional,
  IsString,
  IsUrl,
  Length,
  Min,
} from "class-validator";

export class CreateProductDto {
  @ApiProperty({ example: "Kopi Arabika Gayo Grade A", maxLength: 255 })
  @IsString()
  @Length(1, 255)
  name!: string;

  @ApiProperty({
    example:
      "Kopi arabika specialty dari Aceh Tengah, proses semi-washed, cocok untuk pasar roastery premium.",
    maxLength: 5000,
  })
  @IsString()
  @Length(10, 5000)
  description!: string;

  @ApiProperty({ example: 50, minimum: 1 })
  @IsInt()
  @Min(1)
  moq!: number;

  @ApiProperty({ example: 10000, minimum: 1 })
  @IsInt()
  @Min(1)
  monthlyCapacity!: number;

  @ApiProperty({ example: 5.5, minimum: 0 })
  @IsNumber()
  @Min(0)
  priceMin!: number;

  @ApiProperty({ example: 6.5, minimum: 0 })
  @IsNumber()
  @Min(0)
  priceMax!: number;

  @ApiProperty({
    example: 3.5,
    minimum: 0,
    description: "Accepted from owner only.",
  })
  @IsNumber()
  @Min(0)
  hpp!: number; // accepted from owner only, never returned

  @ApiPropertyOptional({
    example: [
      "https://storage.tradeconnect.id/products/gayo-grade-a-1.jpg",
      "https://storage.tradeconnect.id/products/gayo-grade-a-2.jpg",
    ],
    type: [String],
  })
  @IsArray()
  @IsUrl({}, { each: true })
  @IsOptional()
  photoUrls?: string[];
}
