import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import { IsOptional, IsString, Length, Matches } from "class-validator";

export class CreateUmkmDto {
  @ApiProperty({ example: "CV Kopi Gayo Nusantara", maxLength: 255 })
  @IsString()
  @Length(1, 255)
  legalName!: string;

  @ApiProperty({ example: "1234567890123", pattern: "^\\d{13}$" })
  @IsString()
  @Matches(/^\d{13}$/, { message: "NIB must be exactly 13 digits" })
  nib!: string;

  @ApiPropertyOptional({
    example: "Produsen kopi arabika specialty dari Takengon, Aceh Tengah.",
  })
  @IsString()
  @IsOptional()
  description?: string;
}
