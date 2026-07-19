import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsDateString, IsOptional, IsString, Length } from 'class-validator';

export class CreateReminderDto {
  @ApiProperty({ example: 'Kirim dokumen penawaran ke GlobalTech' })
  @IsString()
  @Length(1, 255)
  title!: string;

  @ApiProperty({ example: '2026-07-20T09:00:00.000Z', description: 'ISO datetime' })
  @IsDateString()
  remindAt!: string;

  @ApiPropertyOptional({ example: 'Email Penawaran', default: 'general' })
  @IsOptional()
  @IsString()
  @Length(1, 64)
  type?: string;
}
