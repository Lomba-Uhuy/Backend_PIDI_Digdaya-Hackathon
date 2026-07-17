import { ApiPropertyOptional } from '@nestjs/swagger';
import { IsOptional, IsString, Length } from 'class-validator';

export class UpdateUmkmDto {
  @ApiPropertyOptional({ example: 'CV Kopi Gayo Nusantara', maxLength: 255 })
  @IsOptional()
  @IsString()
  @Length(1, 255)
  legalName?: string;

  @ApiPropertyOptional({ example: 'Produsen kopi arabika specialty dari Takengon.' })
  @IsOptional()
  @IsString()
  description?: string;
}
