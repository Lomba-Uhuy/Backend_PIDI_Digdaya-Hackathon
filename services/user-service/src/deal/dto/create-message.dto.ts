import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsIn, IsOptional, IsString, Length } from 'class-validator';

export const MESSAGE_SENDERS = ['umkm', 'buyer', 'system'] as const;

export class CreateMessageDto {
  @ApiProperty({ example: 'Kami dapat menyetujui $2.70/kg untuk pesanan trial.' })
  @IsString()
  @Length(1, 8000)
  text!: string;

  @ApiPropertyOptional({
    enum: MESSAGE_SENDERS,
    default: 'umkm',
    description: 'Author. Defaults to umkm (the caller). buyer turns are AI-simulated.',
  })
  @IsOptional()
  @IsIn(MESSAGE_SENDERS)
  sender?: (typeof MESSAGE_SENDERS)[number];

  @ApiPropertyOptional({ description: 'Detected/assigned intent for this message' })
  @IsOptional()
  @IsString()
  @Length(1, 32)
  intent?: string;
}
