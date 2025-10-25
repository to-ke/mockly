import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/cn'


const buttonVariants = cva(
    'inline-flex items-center justify-center whitespace-nowrap rounded-2xl text-sm font-medium transition-colors duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none border active:translate-y-[1px]',
    {
        variants: {
            variant: {
                default: 'bg-primary text-primary-foreground hover:opacity-90 border-transparent',
                ghost: 'bg-transparent hover:bg-accent border-transparent',
                outline: 'bg-transparent border-border hover:bg-accent',
                destructive: 'bg-destructive text-destructive-foreground border-transparent hover:opacity-90',
            },
            size: {
                sm: 'h-8 px-3',
                md: 'h-10 px-4',
                lg: 'h-12 px-5 text-base',
            },
        },
        defaultVariants: { variant: 'default', size: 'md' },
    }
)


export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
    asChild?: boolean
}


export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
})
Button.displayName = 'Button'
