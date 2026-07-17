import { ApiProperty } from "@nestjs/swagger";
import { IsEmail, IsString, MinLength } from "class-validator";

export class AuthRegisterDto {
  @ApiProperty({
    example: "owner@kopigayo.id",
    format: "email",
    description: "Must be a unique email address",
  })
  @IsEmail()
  email!: string;

  @ApiProperty({
    example: "KopiGayo!2026",
    minLength: 8,
    description: "Minimum 8 characters",
  })
  @IsString()
  @MinLength(8)
  password!: string;
}
