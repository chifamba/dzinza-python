import React from 'react';

// Simple unique id generator for test compatibility
let __formFieldIdCounter = 0;
function generateFieldId(name?: string) {
  __formFieldIdCounter += 1;
  return name ? `field-${name}-${__formFieldIdCounter}` : `field-${__formFieldIdCounter}`;
}

// Enhanced Form component with proper props, filtering out non-DOM props
export const Form = ({ 
  children, 
  handleSubmit, // filter out
  formState, // filter out
  setValue, // filter out
  getValues, // filter out
  register, // filter out
  reset, // filter out
  watch, // filter out
  ...props 
}: { 
  children: React.ReactNode; 
  [key: string]: any;
}) => (
  <form {...props}>{children}</form>
);

// FormProvider component for react-hook-form contexts without creating a form element
export const FormProvider = ({ 
  children, 
  ...props 
}: { 
  children: React.ReactNode; 
  [key: string]: any;
}) => (
  <div {...props}>{children}</div>
);

// FormItem forwards ref and className
export const FormItem = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ children, className, ...props }, ref) => (
    <div ref={ref} className={className} {...props}>{children}</div>
  )
);
FormItem.displayName = 'FormItem';

// FormControl forwards ref
export const FormControl = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ children, ...props }, ref) => (
    <div ref={ref} {...props}>{children}</div>
  )
);
FormControl.displayName = 'FormControl';

// FormField filters out non-DOM props and provides field object to render
export const FormField = ({ 
  children,
  control,
  name,
  render,
  ...props 
}: { 
  children?: React.ReactNode;
  control?: any;
  name?: string;
  render?: (props: any) => React.ReactNode;
  [key: string]: any;
}) => {
  // Generate a unique id for this field instance
  const id = React.useMemo(() => generateFieldId(name), [name]);
  const labelId = `${id}-label`;
  if (render) {
    let value = '';
    if (control && typeof control.getValues === 'function' && name) {
      value = control.getValues(name) ?? '';
    }
    const field = {
      name: name || '',
      value,
      onChange: (e: any) => {},
      onBlur: () => {},
      ref: { current: null },
      id,
      labelId,
    };
    // Only pass DOM-safe props
    const domProps = Object.fromEntries(Object.entries(props).filter(([k]) => !['handleSubmit','formState','setValue','getValues','register','reset','watch'].includes(k)));
    return <div {...domProps}>{render({ field, id, labelId })}</div>;
  }
  // Only pass DOM-safe props
  const domProps = Object.fromEntries(Object.entries(props).filter(([k]) => !['handleSubmit','formState','setValue','getValues','register','reset','watch'].includes(k)));
  return <div {...domProps}>{children}</div>;
};

export const FormDescription = ({ 
  children,
  ...props 
}: { 
  children: React.ReactNode;
  [key: string]: any;
}) => (
  <p {...props}>{children}</p>
);

// FormLabel: add htmlFor if name/id is provided
export const FormLabel = React.forwardRef<HTMLLabelElement, React.LabelHTMLAttributes<HTMLLabelElement>>(
  ({ children, htmlFor, id, ...props }, ref) => (
    <label ref={ref} htmlFor={htmlFor || id} id={id} {...props}>{children}</label>
  )
);
FormLabel.displayName = 'FormLabel';

// FormMessage: always use <span> for accessibility
export const FormMessage = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ children, ...props }, ref) => (
    <span ref={ref} role="alert" aria-live="polite" {...props}>{children}</span>
  )
);
FormMessage.displayName = 'FormMessage';
