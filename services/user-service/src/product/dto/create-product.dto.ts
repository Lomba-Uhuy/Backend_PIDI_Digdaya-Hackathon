import { IsArray, IsInt, IsNumber, IsOptional, IsString, IsUrl, Length, Min } from 'class-validator';

export class CreateProductDto {
  @IsString() @Length(1, 255)
  name!: string;

  @IsString() @Length(10, 5000)
  description!: string;

  @IsInt() @Min(1)
  moq!: number;

  @IsInt() @Min(1)
  monthlyCapacity!: number;

  @IsNumber() @Min(0)
  priceMin!: number;

  @IsNumber() @Min(0)
  priceMax!: number;

  @IsNumber() @Min(0)
  hpp!: number; // accepted from owner only, never returned

  @IsArray()
  @IsUrl({}, { each: true })
  @IsOptional()
  photoUrls?: string[];
}