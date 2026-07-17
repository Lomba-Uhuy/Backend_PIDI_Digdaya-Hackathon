import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsInt, IsOptional, IsString, Min } from 'class-validator';

export class HsClassifyDto {
  @ApiProperty({
    example:
      'Kopi arabika roasted whole bean dari Gayo Aceh. Specialty grade, fermentasi 72 jam, dried natural.',
  })
  @IsString()
  description!: string;

  @ApiPropertyOptional({ example: 3, minimum: 1, maximum: 10 })
  @IsInt()
  @Min(1)
  @IsOptional()
  top_k?: number;
}
