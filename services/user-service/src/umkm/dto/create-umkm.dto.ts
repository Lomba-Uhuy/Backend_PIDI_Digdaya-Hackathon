import { IsOptional, IsString, Length, Matches } from 'class-validator';

export class CreateUmkmDto {
  @IsString()
  @Length(1, 255)
  legalName!: string;

  @IsString()
  @Matches(/^\d{13}$/, { message: 'NIB must be exactly 13 digits' })
  nib!: string;

  @IsString()
  @IsOptional()
  description?: string;
}